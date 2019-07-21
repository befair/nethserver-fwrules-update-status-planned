# NethServer Firewall Iprange Rules Updater

1. Create hours ranges for your week in e-smith including "closing hours" as:

    ```
    for day_of_week in 1 2 3 4 5 6; do
        /sbin/e-smith/db /var/lib/nethserver/db/weekly-hours set $day_of_week timing 1 8:00 2 9:00 3 10:00 4 11:00 5 12:00 close1 13:30 6 14:00 7 15:00 8 16:00 9 17:00 10 18:00 close2 19:00;
    done
    ```

2. Define some firewall objects as "iprange" starting with `lab_`
3. Define some firewall rules that match those "iprange" as Src
4. Place this directory in `/usr/share/cockpit` of your NethSecurity firewall

and ... enjoy!

## Apply rules

Rules may not be applied synchronously, because there is a (inotify) trigger when the plan is updated.
The trigger checks if it is the time of updating firewall rules, in that case, it sleeps 1 minute and then apply the new plan.

When the plan is updated, the script `update-plan.py` creates systemd timers corresponding to services
([ending with '@'](https://serverfault.com/questions/896335/how-to-distinguish-between-systemd-unit-run-manually-or-by-timer))
all created in`/etc/systemd/system/`:

- `fwrules-enable`: 15 mins before starting hour
- `fwrules-disable`: 15 mins after ending hour

Services then are invoked with rules list separated by comma as aliases (i.e.: fwrules-enable@2,3,4 to enable rules 2 and 3 and 4)

And they in turn calls the script `bin/apply-rules.py [enable|disable] [rules1,..,rulesN]`

## Requirements

`yum install python-pip`
`pip install python-inotify`


### Enable a specific group to manage firewall rules
#
#1. Add users to a dedicated group (i.e: "docenti")
#2. Copy `99_nethserver_fwrules.sudoers` in `/etc/sudoers.d/99_nethserver_fwrules` (WARNING: remove ".sudoers" extension)
#
#Optional: if you want to enable all rules at midnight
#
#3. Copy `nethserver_fwrules.cron` in `/etc/cron.d/nethserver_fwrules`
