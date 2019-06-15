# NethServer Firewall Iprange Rules Updater

1. Create hours ranges for your week as:

    for i in LUN MAR MER GIO VEN SAB DOM; do
        /sbin/e-smith/db /var/lib/nethserver/db/weekly-hours set $i timing 1 8:00 2 9:00 3 10:00 4 11:00 5 12:00;
    done

1. Define some firewall objects as "iprange"
2. Define some firewall rules that match those "iprange" as Src
3. Place this directory in `/usr/share/cockpit` of your NethSecurity firewall

and ... enjoy!

## Enable a specific group to manage firewall rules

1. Add users to a dedicated group (i.e: "docenti")
2. Copy `99_nethserver_fwrules.sudoers` in `/etc/sudoers.d/99_nethserver_fwrules` (WARNING: remove ".sudoers" extension)

Optional: if you want to enable all rules at midnight

3. Copy `nethserver_fwrules.cron` in `/etc/cron.d/nethserver_fwrules`
