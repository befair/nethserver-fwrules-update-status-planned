# NethServer Firewall Iprange Rules Updater

1. Define some firewall objects as "iprange"
2. Define some firewall rules that match those "iprange" as Src
3. Place this directory in `/usr/share/cockpit` of your NethSecurity firewall

and ... enjoy!

## Enable a specific group to manage firewall rules

1. Add users to a dedicated group (i.e: "docenti")
2. Copy `99_nethserver_fwrules.sudoers` in `/etc/sudoers.d/99_nethserver_fwrules` (TODO FIXME see nethserver documentation for templates)
