import json
import subprocess
from datetime import datetime

# Command to change FW rules
CMD="/sbin/e-smith/db"
DB="/var/lib/nethserver/db/fwrules-plan"

# Get current week day number
dow = datetime.now().strftime("%u")

# Get current FW rules
rules = json.loads(subprocess.check_output([CMD, DB, "printjson", dow]))

# Retrive and clean all rules
for rule in rules['props']:
    subprocess.call([CMD, DB, "setprop", dow, rule, ""])
