var result = $("#result");
var e_smith_fname_hours = '/var/lib/nethserver/db/weekly-hours';
var e_smith_fname_plan = '/var/lib/nethserver/db/fwrules-plan';
var e_smith_fname = '/var/lib/nethserver/db/fwrules.carducci-galilei';
var n_rules_to_apply = 0; //Global counter for number of rules
var n_rules_applied = 0;  //Global counter for number of applied rules

var day_hours = [];       //List of { day: DAYNUM, hour: HOUR }
var super_headers = [];   // List of { DAYs: NHOURS (colspan) }
var sub_headers = [];     // List of { HOURs: (colspan = 1) }
var DAYS = {
    1: "LUN", 2: "MAR", 3: "MER", 4: "GIO", 5: "VEN", 6: "SAB", 7: "DOM"
};

$(document).ready(hours_load);


/***************************************
 * BEGIN header loading with hours info
 ***************************************/
function generate_th_rows(el) {
    return '<th colspan="' + el.colspan + '" align="center">' + el.val + '</th>';
}

function load_thead(data) {
    let obj = JSON.parse(data);
    let html = '';
    for (k in obj) {
        let timing = obj[k];
        super_headers.push({ 'val': DAYS[timing.name], 'colspan': Object.keys(timing.props).length });
        for (let c=1; c<=Object.keys(timing.props).length; c++) {
            sub_headers.push({'val': c, 'colspan': 1});
            day_hours.push({'day': timing.name, 'hour': timing.props[c]});
        }
    }
    $('#fwrules-thead').prepend("<tr><th></th>" + sub_headers.map(generate_th_rows) + "</tr>");
    $('#fwrules-thead').prepend("<tr><th>LUOGO</th>" + super_headers.map(generate_th_rows) + "</tr>");

    fwrules_planned_load();
    $("#fwrules-update").on("click", fwrules_update);
}

function hours_load() {
    var proc = cockpit.spawn(["/usr/bin/sudo", "/sbin/e-smith/db", e_smith_fname_hours, 'printjson']);
    // proc.done(do_success);
    proc.stream(load_thead);
    proc.fail(do_fail);
    result.empty();
}
/****************************
 * END header generation *
 * BEGIN body generation
 ***************************/

function generate_row(fwrule) {
    let html = '<tr>';
    html += '<td><label class="control-label" for="fwrule-n' + fwrule.name + '">' + fwrule.props.Description + '</label></td>';
    for (k in day_hours) {
        let el = day_hours[k];
        html += '<td><input class="form-control" type="checkbox" name="fwrule-status" data-fwrule="' + fwrule.name + '" data-day="'+ el.day + '" data-hour="' + el.hour +'" ';
        if (fwrule.props.status == "disabled") {
            html += ' checked ></td>';
        } else {
            html += '></td>';
        }
        html += '</td>';
    }
    html += '</tr>';
    return html;
}

function load_tbody(data) {
    let obj = JSON.parse(data);
    let html = '';
    for (k in obj) {
        let fwrule = obj[k];
        if (fwrule.props) {
            if (fwrule.props.Src.startsWith("iprange;")) {
                n_rules_to_apply += 1;
                html += generate_row(fwrule);
            }
        }
    }
    if (html)
        $('#fwrules-tbody').prepend(html);
}

function fwrules_planned_load() {
    var proc = cockpit.spawn(["/usr/bin/sudo", "/sbin/e-smith/db", e_smith_fname, 'printjson']);
    // proc.done(do_success);
    proc.stream(load_tbody);
    proc.fail(do_fail);

    result.empty();
}

/**********************************
 * END body generation
 *********************************/

function fwrules_update() {
    var e_smith_key = 0;
    var e_smith_prop = '';
    var e_smith_struct = [];
    n_rules_applied = 0;
    $('input[type=checkbox]').each(function() {

        let self = $(this);
        let status = "enabled";
        if (this.checked) {
            status = "disabled";

            // Build e-smith structure to be passed to the db "set" command
            // Struct is like: {
            //   "nday": { "hour": ["fwrulen", .... ]}
            e_smith_key = self.attr('data-day');
            if (!e_smith_struct[e_smith_key]) {
                e_smith_struct[e_smith_key] = {};
            }
            let h = self.attr('data-hour');
            if (!e_smith_struct[e_smith_key][h]) {
                e_smith_struct[e_smith_key][h] = [self.attr('data-fwrule')];
            } else {
                e_smith_struct[e_smith_key][h].push(self.attr('data-fwrule'));
            }
        }
    });

    // Define firewall plans -- only used to disable rules
    for (k in DAYS) {
        let props = [];
        if (k in e_smith_struct) {
            let props_obj = e_smith_struct[k];
            for (khour in props_obj) {
                props.push(khour);
                props.push(props_obj[khour].toString());
            }
        } else {
            props = [];
        }
        var proc = cockpit.spawn(['/usr/bin/sudo', '/sbin/e-smith/db', e_smith_fname_plan, 'set', k, "configuration"].concat(props));
        proc.done(do_success);
        proc.fail(do_fail);

        result.empty();
    };
}

// Step 2
/* function firewall_adjust() {
    n_rules_applied += 1;

    if (n_rules_to_apply == n_rules_applied) {
        var proc = cockpit.spawn(["/usr/bin/sudo", '/sbin/e-smith/signal-event', 'firewall-adjust']);
        proc.done(do_success_applied);
        proc.stream(append_output);
        proc.fail(do_fail);
        result.empty();
        n_rules_applied = 0;
    }
}*/

function do_success() {
    result.css("color", "green");
    result.text("success");
}

function do_success_applied() {
    do_success();

    $('input[type=checkbox]').each(function() {
        if (!this.checked) {
            $(this).parent().next().text("navigazione bloccata");
        } else {
            $(this).parent().next().text("navigazione consentita");
        }
    });
}

function do_fail() {
    result.css("color", "red");
    result.text("fail");
}

function append_output(data) {
    output.append(document.createTextNode(data));
}

