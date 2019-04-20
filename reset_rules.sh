#!/bin/bash

# Enable all rules related to "ipranges"

E_SMITH_CMD="/sbin/e-smith/db /var/lib/nethserver/db/fwrules"

$E_SMITH_CMD print | grep "iprange;" | cut -d'=' -f1 | while read rulenum; do
    $E_SMITH_CMD setprop $rulenum status enabled
done

/sbin/e-smith/signal-event firewall-adjust
