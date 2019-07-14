"""
FWPLAN RULES:

All-in-one script file to manage systemd timers.
Include systemd units initialization if not found.
"""

import inotify.adapters, inotify.constants
import csv
from datetime import datetime, timedelta, time

# --- Configuration ---

PATH_WEEKLY_HOURS = '/home/fero/src/befair/nethserver-fwrules-update-status-planned/doc/weekly-hours-output'
PATH_FWRULES_PLAN = '/home/fero/src/befair/nethserver-fwrules-update-status-planned/doc/weekly-hours-output'
PATH_BASENAME_SYSTEMD = '/etc/systemd/system/fwrules-{kind}'
DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
MINUTES_THRESHOLD = 15

TEMPLATE_SYSTEMD_TIMER="""
[Unit]
Description=Enable fwrules for {dow} {time}

[Timer]
OnCalendar={dow} {time}
Unit=fwrules-{kind}@{rules}.service
Persistent=true

[Install]
WantedBy=timers.target
"""

# --- Setup ---

for kind in ('enable', 'disable'):
    path_systemd = PATH_BASENAME_SYSTEMD.format(kind=kind)
    if not os.path.exists(path_systemd):
        with open(path_systemd, "w") as f:
            f.write("""
[Unit]
Description=Firewall {kind} rules %i

[Service]
Type=oneshot
ExecStart=/usr/share/cockpit/nethserver-fwrules-update-status-planned/bin/apply-rules.py {kind} %i

[Install]
WantedBy = multi-user.target
""".format(kind=kind)

# TODO -- setup default weekly hours?



def fwplan_create_timers_for_hour(dow_int, dt_hour, rules_to_enable=[], rules_enabled=[]):
    """
    Create systemd timers and service by hour.

    """

    dow = DOW[dow_int]

    # Set starting hours 15 minutes before hour starts
    hour_start = dt_hour - timedelta(minutes=MINUTES_THRESHOLD)
    hour_start_str= hour_start.time().strftime("%H:%M")

    # Create timers
    print(TEMPLATE_SYSTEMD_TIMER.format(
        kind='enable', rules=",".join(rules_to_enable),
        dow=dow, time=hour_start_str)

    # For each rule previously enabled
    rules_to_disable = set(rules_enabled) - set(rules_to_enable)

    if rules_to_disable:
        # Set ending hours 15 minutes after hour ends
        hour_end = dt_hour + timedelta(minutes=MINUTES_THRESHOLD)
        hour_end_str= hour_end.time().strftime("%H:%M")

        timer_date="{} {}".format(dow, ",".join(hours_end_strs))
        print("OnCalendar={}".format(timer_date))

    # Update rules previously enabled
    rules_enabled = rules_to_enable


def fwplan_create_timers_for_day(dow_int, dt_hours, fwrules_plan):
    """
    For a specific day and specific hours,
    create timers and services to enable/disable firewall rules
    """

    # Find fwrules for the day:
    for fwrule_plan in fwrules_plan:
        if dow_int == int(fwrule_plan["name"]):
            # parse rules dict as with { datetime_hour: rules_list, ... }
            day_fwrules_to_enable = {
                    datetime.strptime(x, "%H:%M"): y.split(",")
                    for x, y in fwrule_plan["props"].items() }

            # For each day hour of the day
            # If fwrules to enable are present => create "enable rule"
            # While keeping track of enabled rules
            # If fwrules to enable are not present => create "disable rule"
            rules_already_enabled=[]
            for dt_hour in dt_hours:
                fwplan_create_timers_for_hour(
                        dow_int, dt_hour, day_fwrules_to_enable.get(dt_hour), rules_enabled=rules_enabled)


def read_fwplan(dow_int_needed=None):
    """
    1. db weekly-hours printjson
    1. db fwrules-plan printjson
    2. for each day
        3. sort hours with strptime
        4. for each hour:
            5. create timer to open corresponding rules and keep track of new open and closed rules
            6. create timer to close rules that were closed in the previous hour
    """

    weekly_hours = json.load("../doc/weekly-hours.json")
    fwrules_plan = json.load("../doc/fwrules-plan.json")
    for day_hours in weekly_hours:
        dow_int = int(day_hours["name"])  # TODO: name it with real dow? i.e: Mon, Tue, ...
        if dow_int_needed and dow_int != dow_int_needed:
            continue

        # Parse hours
        hours = [datetime.strptime(x, "%H:%M") for x in day_hours["props"].values()]
        hours.sort()

        fwplan_create_timers_for_day(dow_int, dt_hours, fwrules_plan)



def _main():
    i = inotify.adapters.Inotify()

    # Watch for changes in weekly hours definition
    i.add_watch(PATH_FWRULES_PLAN,
            mask=inotify.constants.IN_CLOSE_WRITE)

    # Listen indefinely for events
    for event in i.event_gen(yield_nones=False):
        (_, type_names, path, filename) = event

        # Be careful: does not work in vim that create a new file and overwrite
        if type_names[0] == 'IN_CLOSE_WRITE':
            # If written => read file and regenerate timers
            read_weekly_hours()



if __name__ == '__main__':
    _main()
