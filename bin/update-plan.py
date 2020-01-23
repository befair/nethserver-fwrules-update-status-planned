#!/usr/bin/env python
"""
FWPLAN RULES:

All-in-one script file to manage systemd timers.
Include systemd units initialization if not found.
"""

import csv
import json
import logging
import os
import subprocess
import time
from datetime import datetime, timedelta

import inotify.adapters
import inotify.constants

# --- Configuration ---
DEBUG = os.environ.get('APP_DEBUG', False)

# TODO: backend driver class to manage input from e-smith or from json files for mockups
BASEDIR = os.environ.get('APP_BASEDIR', '/var/lib/nethserver/db/')
PATH_WEEKLY_HOURS = os.path.join(BASEDIR, 'weekly-hours')
PATH_FWRULES_PLAN = os.path.join(BASEDIR, 'fwrules-plan')
PATH_FWRULES = os.path.join(BASEDIR, 'fwrules')
PATH_BASENAME_SYSTEMD = '/etc/systemd/system/fwrules-{kind}'
DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
MINUTES_THRESHOLD = os.environ.get('APP_MINUTES_THRESHOLD', 5)
RULESRC_STARTSWITH = "iprange;lab_"
LOG_FILE = "/var/log/nethserver-fwrules-updater.log"

TEMPLATE_SYSTEMD_TIMER="""
[Unit]
Description={kind} fwrules for {dow} {time}

[Timer]
OnCalendar={dow} {time}
Unit=fwrules-{kind}@{rules}.service
Persistent=true

[Install]
WantedBy=timers.target
"""

# --- Setup ---
# Create systemd services

if not DEBUG:
    for kind in ('disable', 'enable'):
        path_systemd = PATH_BASENAME_SYSTEMD.format(kind=kind) + "@.service"
        if not os.path.exists(path_systemd):
            with open(path_systemd, "w") as f:
                f.write("""
    [Unit]
    Description=Firewall {kind} rules %i

    [Service]
    Type=oneshot
    ExecStart=/usr/share/cockpit/nethserver-fwrules-update-status-planned/bin/apply-rules.py {kind}d %i

    [Install]
    WantedBy = multi-user.target
    """.format(kind=kind))

# Setup logging
logging.basicConfig(filename=LOG_FILE,level=logging.INFO, format='[%(asctime)s] %(message)s')


def fwplan_create_timers_for_hour(dow_int, dt_hour, all_fwrules, rules_to_disable=[]):
    """
    Create systemd timers for rules involved in a specific hour.

    * create timer to disable all rules_to_disable at the specific (dow, dt_hour-15mins);
    * create timer to enable all other rules at the specific (dow, dt_hour+15mins)

    NOTE: the operation of enabling/disabling rule is idempotent.
    So we can enable a rule many times, and keep it enabled.
    """

    fname_timers_created = []
    dow = DOW[dow_int - 1]

    # Set starting hours 5 minutes before hour starts
    hour_start = dt_hour - timedelta(minutes=MINUTES_THRESHOLD)
    hour_start_str= hour_start.time().strftime("%H:%M")

    # Create timers
    if rules_to_disable:
        path_systemd = PATH_BASENAME_SYSTEMD.format(kind='disable') + "-{dow}-{hour}.timer".format(dow=dow,hour=hour_start.strftime("%H-%M"))
        if DEBUG:
            print("[DEBUG] Writing {}...".format(path_systemd))
        else:
            with open(path_systemd, "w") as f:
                f.write(TEMPLATE_SYSTEMD_TIMER.format(
                    kind='disable', rules=":".join(rules_to_disable),
                    dow=dow, time=hour_start_str))

        fname_timers_created.append(path_systemd)

    # For each rule previously disabled
    rules_to_enable = set(all_fwrules) - set(rules_to_disable)

    if rules_to_enable:
        # Set ending hours 5 minutes after hour ends
        hour_end = dt_hour + timedelta(minutes=MINUTES_THRESHOLD)
        hour_end_str = hour_end.time().strftime("%H:%M")

        path_systemd = PATH_BASENAME_SYSTEMD.format(kind='enable') + "-{dow}-{hour}.timer".format(dow=dow,hour=hour_end.strftime("%H-%M"))
        if DEBUG:
            print("[DEBUG] Writing {}...".format(path_systemd))
        else:
            with open(path_systemd, "w") as f:
                f.write(TEMPLATE_SYSTEMD_TIMER.format(
                    kind='enable', rules=":".join(rules_to_enable),
                    dow=dow, time=hour_end_str))

        fname_timers_created.append(path_systemd)

    return fname_timers_created


def fwplan_create_timers_for_day(dow_int, dt_hours, fwrules_plan, all_fwrules):
    """
    For a specific day and specific hours,
    create timers and services to disable/enable firewall rules
    """

    fname_timers_created = []

    # Find fwrules for the day:
    for fwrule_plan in fwrules_plan:
        if dow_int == int(fwrule_plan["name"]):
            # parse rules dict as with { datetime_hour: rules_list, ... }
            day_fwrules_to_disable = {
                    datetime.strptime(x, "%H:%M"): y.split(",")
                    for x, y in fwrule_plan.get("props", {}).items() }

            # For each day hour of the day
            # If fwrules to disable are present => create "disable rule"
            # While keeping track of disabled rules
            # If fwrules to disable are not present => create "enable rule"
            for dt_hour in dt_hours:
                fname_timers_created += fwplan_create_timers_for_hour(
                        dow_int, dt_hour, all_fwrules, day_fwrules_to_disable.get(dt_hour, []))

    return fname_timers_created


def read_fwplan(dow_int_needed=None):
    """
    1. db weekly-hours printjson
    1. db fwrules-plan printjson
    1. db fwrules printjson
    2. for each day
        3. sort hours with strptime
        4. for each hour:
            5. create timer to open corresponding rules and keep track of new open and closed rules
            6. create timer to close rules that were closed in the previous hour
    """

    weekly_hours_json = subprocess.check_output(["/sbin/e-smith/db", PATH_WEEKLY_HOURS, "printjson"])
    weekly_hours = json.loads(weekly_hours_json)
    fwrules_plan_json = subprocess.check_output(["/sbin/e-smith/db", PATH_FWRULES_PLAN, "printjson"])
    fwrules_plan = json.loads(fwrules_plan_json)
    fwrules_json = subprocess.check_output(["/sbin/e-smith/db", PATH_FWRULES, "printjson"])
    fwrules = json.loads(fwrules_json)
    all_fwrules = [ x["name"] for x in fwrules if x.get("props", {}).get("Src","").startswith(RULESRC_STARTSWITH) ]

    fname_timers_created = []
    for day_hours in weekly_hours:
        dow_int = int(day_hours["name"])  # TODO: name it with real dow? i.e: Mon, Tue, ...
        if dow_int_needed and dow_int != dow_int_needed:
            continue

        # Parse hours
        dt_hours = [datetime.strptime(x[1], "%H:%M") for x in day_hours["props"].items() if not x[0].startswith("close")]
        dt_hours.sort()

        fname_timers_created += fwplan_create_timers_for_day(dow_int, dt_hours, fwrules_plan, all_fwrules)

        # Close hours
        # Create "enable" rules timers for all closing hours
        close_hours = [datetime.strptime(x[1], "%H:%M") for x in day_hours["props"].items() if x[0].startswith("close")]

        for close_hour in close_hours:
            fname_timers_created += fwplan_create_timers_for_hour(dow_int, close_hour, all_fwrules)

    # Enable and start all timers created
    if fname_timers_created and not DEBUG:
        subprocess.check_call(["/usr/bin/systemctl", "enable"] + [os.path.basename(x) for x in fname_timers_created])
        subprocess.check_call(["/usr/bin/systemctl", "start"] + [os.path.basename(x) for x in fname_timers_created])


def _main():
    i = inotify.adapters.Inotify()

    # Watch for changes in weekly hours definition
    i.add_watch(BASEDIR, mask=inotify.constants.IN_CLOSE_WRITE | inotify.constants.IN_MOVED_TO)

    # Listen indefinely for events
    for event in i.event_gen(yield_nones=False):
        (_, type_names, path, filename) = event

        if DEBUG:
            print("PATH=[{}] FILENAME=[{}] EVENT_TYPES={}".format(path, filename, type_names))

        # Be careful: does not work in vim that create a new file and overwrite
        if filename == os.path.basename(PATH_FWRULES_PLAN):

            # If written =>
            # - get a list of previously generated timers and apply a delay if there are timers scheduled in 2 minutes!!
            # - remove previously generated timers
            # - read file and regenerate timers
            dirname = os.path.dirname(PATH_BASENAME_SYSTEMD)
            dt_now = datetime.now()
            dow_int_now = int(dt_now.strftime("%w"))
            waited = False
            filenames = os.listdir(dirname)

            # Check current day rules and apply rules for the current hour
            fwrules_plan_json = subprocess.check_output(["/sbin/e-smith/db", PATH_FWRULES_PLAN, "printjson"])
            fwrules_plan = json.loads(fwrules_plan_json)

            fwrules_json = subprocess.check_output(["/sbin/e-smith/db", PATH_FWRULES, "printjson"])
            fwrules = json.loads(fwrules_json)

            dow_now = dt_now.strftime("%w")

            # Check current day rules and apply changes for the current hour
            for plan in fwrules_plan:
                if plan['name'] == dow_now and 'props' in plan:
                    # Command to instantly enable/disable fw rules
                    cmd = "/usr/share/cockpit/nethserver-fwrules-update-status-planned/bin/apply-rules.py"
                    
                    # Create a list of ordered plan times
                    dt_hours = [datetime.strptime(x, "%H:%M") for x in plan["props"].keys()]
                    dt_hours.sort()

                    # Set initial value for the previous hour
                    prev = dt_hours[0]

                    # Loop till we reach current hour
                    for dt_hour in dt_hours:
                        if dt_hour.time() <= dt_now.time():
                            prev = dt_hour
                        else:
                            break

                    dt_hour_key = prev.strftime("%H:%M")

                    for rule in fwrules:
                        if dt_hour_key not in plan['props']:
                            logging.error("Error in fw_plan: missing key {0}".format(dt_hour_key))
                        else:
                            if rule['name'] in plan['props'][dt_hour_key].split(','):
                                logging.info("Disabling rule '{0}' at hour '{1}'".format(rule['name'], dt_hour_key))
                                subprocess.check_output([cmd, 'disabled', rule['name']])
                            else:
                                logging.info("Enabling rule '{0}' at hour '{1}'".format(rule['name'], dt_hour_key))
                                subprocess.check_output([cmd, 'enabled', rule['name']])
            
            for kind in ("disable", "enable"):
                fname_start = os.path.basename(PATH_BASENAME_SYSTEMD).format(kind=kind)
                timer_names = [ fname for fname in filenames if fname.startswith(fname_start) and fname.endswith(".timer")]

                # 1. Parse timer name
                for fname in timer_names:
                    dow_and_time = fname[len(fname_start) + 1:-len(".timer")]
                    dow, hour, minute = dow_and_time.split("-")
                    dow_int = DOW.index(dow) + 1

                    if dow_int == dow_int_now:
                        # If the timer is for the current day
                        # Check if timedelta from now is <= 2 minutes
                        # if it is => delay for 5 minutes and exit from all loops
                        # if not => proceed in deleting timers
                        dt_timer = datetime(dt_now.year, dt_now.month, dt_now.day, int(hour), int(minute))

                        if abs(dt_now - dt_timer) < timedelta(minutes=2):
                            time.sleep(360)
                            waited = True
                            break

                if waited:
                    break

            # Step 2.
            # - Stop and disable all timers created
            # - Remove all previously generated timers
            if timer_names and not DEBUG:
                subprocess.check_output(["/usr/bin/systemctl", "stop"] + timer_names)
                subprocess.check_output(["/usr/bin/systemctl", "disable"] + timer_names)
                for fname in timer_names:
                    abs_fname = os.path.join(os.path.dirname(PATH_BASENAME_SYSTEMD), fname)
                    os.remove(abs_fname)

            logging.info("Creating week timers...")
            # Step 3. read new plan and create new timers to apply rules
            read_fwplan()


if __name__ == '__main__':
    _main()
