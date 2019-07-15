#!/usr/bin/env python
"""
Enable/Disable NethServer firewall rules
"""
import sys
import subprocess

PATH_E_SMITH_FWRULES = '/var/lib/nethserver/db/fwrules'
PATH_E_SMITH_BIN = '/sbin/e-smith/'

if __name__ == "__main__":

    # par 1: enable/disable
    # par 2: rule1,rule2,...,ruleN
    try:
        status = sys.argv[1]
        fwrules = sys.argv[2].split(",")
    except IndexError:
        print("Usage: {} <enable|disable> rules1[,rules2,...,rulesN]".format(sys.argv[0]))
        sys.exit(100)


    # Step 1: set status rules with e-smith
    for e_smith_key in fwrules:
        subprocess.check_output([PATH_E_SMITH_BIN + 'db', PATH_E_SMITH_FWRULES, 'setprop', e_smith_key, 'status', status])

    # Step 2: signal-event firewall
    subprocess.check_output([PATH_E_SMITH_BIN + 'signal-event', 'firewall-adjust'])

