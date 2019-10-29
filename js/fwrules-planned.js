var result = $("#result");
var e_smith_fname_hours = '/var/lib/nethserver/db/weekly-hours';
var e_smith_fname_plan = '/var/lib/nethserver/db/fwrules-plan';
var e_smith_fname = '/var/lib/nethserver/db/fwrules';

var FWRULES = [];
var FWRULES_PLAN = [
    {"name": "1", "type": "configuration"},
    {"name": "2", "type": "configuration"},
    {"name": "3", "type": "configuration"},
    {"name": "4", "type": "configuration"},
    {"name": "5", "type": "configuration"},
    {"name": "6", "type": "configuration"},
    {"name": "7", "type": "configuration"}
];

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
        for (hour_n in timing.props) {
            if (parseInt(hour_n)) {
                sub_headers.push({'val': hour_n, 'colspan': 1});
                day_hours.push({'day': timing.name, 'hour': timing.props[hour_n]});
            }
        }
    }
    $('#fwrules-thead').prepend("<tr><th></th>" + sub_headers.map(generate_th_rows) + "</tr>");
    $('#fwrules-thead').prepend("<tr><th>LUOGO</th>" + super_headers.map(generate_th_rows) + "</tr>");

    fwrules_planned_load();
    $("#fwrules-update").on("click", on_submit);
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

function is_open(fwrule, el, open_hours) {
    let result = false;

    let open_day = open_hours[el.day];
    if (open_day && open_day[el.hour]) {
        //check if the rule is here as a value
        let open_places = open_day[el.hour].split(",");
        if (open_places.indexOf(fwrule.name) != -1)
            result = true;
    }

    return result;

}

function generate_row(fwrule, open_hours) {
    var curr_hour = get_current_hour(day_hours);
    
    let html = '<tr>';
    html += '<td><label class="control-label" for="fwrule-n' + fwrule.name + '">' + fwrule.props.Description + '</label></td>';
    // console.log(day_hours);
    
    for (k in day_hours) {
        let el = day_hours[k];
        let title = fwrule.props.Description + ' - ' + DAYS[el.day] + ' ' + el.hour;
        
        // Highlight the current hour
        if(el.hour == curr_hour) {
            html += '<td class="highlight"><input class="form-control checkbox" title="'+ title +'" type="checkbox" name="fwrule-status" data-fwrule="' + fwrule.name + '" data-day="'+ el.day + '" data-hour="' + el.hour +'"';
        } else {
            html += '<td><input class="form-control checkbox" title="'+ title +'" type="checkbox" name="fwrule-status" data-fwrule="' + fwrule.name + '" data-day="'+ el.day + '" data-hour="' + el.hour +'" ';
        }

        if (is_open(fwrule, el, open_hours)) {
            html += ' checked ></td>';
        } else {
            html += '></td>';
        }
        html += '</td>';
    }
    html += '</tr>';
    return html;
}

function load_fwrules(data) {
    FWRULES = JSON.parse(data);
    let proc = cockpit.spawn(["/usr/bin/sudo", "/sbin/e-smith/db", e_smith_fname_plan, 'printjson']);
    proc.stream(load_tbody);
    proc.fail(do_fail);
}

function get_open_hours(e_smith_json) {
    let open_hours = {};
    for (k in e_smith_json) {
        let obj = e_smith_json[k];
        open_hours[obj.name] = obj.props;
    }
    return open_hours;
}


function load_tbody(data) {
    let open_hours = get_open_hours(JSON.parse(data));

    let html = '';
    for (k in FWRULES) {
        let fwrule = FWRULES[k];
        if (fwrule.props && fwrule.props.Src) {
            if (fwrule.props.Src.startsWith("iprange;lab_")) {
                n_rules_to_apply += 1;
                html += generate_row(fwrule, open_hours);
            }
        }
    }
    if (html)
        $('#fwrules-tbody').prepend(html);
}

function fwrules_planned_load() {
    var proc = cockpit.spawn(["/usr/bin/sudo", "/sbin/e-smith/db", e_smith_fname, 'printjson']);
    // proc.done(do_success);
    proc.stream(load_fwrules);
    proc.fail(do_fail);

    result.empty();
}

function get_current_hour(day_hours) {
    // Get day/hour to highlight current hour
    var date = new Date;
    var dt_hour = new Date;
    var day = date.getDay();

    var prev;

    // Set minutes of current time to 0
    date.setMinutes(0);

    day_hours.forEach(function(val) {
        if(day == val['day']) {
            dt_hour.setHours(parseInt(val['hour'].split(':')[0]));
            dt_hour.setMinutes(parseInt(val['hour'].split(':')[1]));

            if(dt_hour <= date)
                prev = val['hour'];
        }
    });
    
    return prev;
}

/**********************************
 * END body generation
 *********************************/

function fwrules_update() {
    var e_smith_key = 0;
    var e_smith_prop = '';
    var e_smith_struct = {};
    n_rules_applied = 0;
    $('input[type=checkbox]').each(function() {

        let self = $(this);

        // Build e-smith structure to be passed to the db "set" command
        // Struct is like: {
        //   "nday": { "hour": "fwrule1,fwrule2,..." }
        e_smith_key = self.attr('data-day');
        let h = self.attr('data-hour');
        if (!e_smith_struct[e_smith_key]) {
            e_smith_struct[e_smith_key] = {};
        }
        if (!e_smith_struct[e_smith_key][h])
            e_smith_struct[e_smith_key][h] = [];

        let status = "enabled";
        if (this.checked) {
            status = "disabled";
            e_smith_struct[e_smith_key][h].push(self.attr('data-fwrule'));
        }
    });

    for (e_smith_key in e_smith_struct) {
        let el = e_smith_struct[e_smith_key];
        for (h in el) {
            // NOTE: rules list become a string split by ","
            el[h] = el[h].toString();
        }
    }

    // Define firewall plans
    for (i_daily_plan in FWRULES_PLAN) {
        let daily_plan = FWRULES_PLAN[i_daily_plan];

        // Take new day plan from e_smith_struct
        let new_plan = e_smith_struct[daily_plan.name];
        if (new_plan)
            daily_plan.props = new_plan;
    };
    /* WARNING - IMPORTANT: e-smith must do "setjson" in order to be atomic and
     * avoid multiple serverside events (inotify) management */
    let proc = cockpit.spawn(['/usr/bin/sudo', '/sbin/e-smith/db', e_smith_fname_plan, 'setjson', JSON.stringify(FWRULES_PLAN)]);
    proc.done(do_success);
    proc.fail(do_fail);

    result.empty();
}


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

function on_submit() {
    display_loading();
    fwrules_update();
}

function display_loading() {
    document.getElementById("loader").style.display="unset";
    document.getElementById("fwrules-update").style.display="none";
    document.getElementsByClassName("container-fluid")[0].style.opacity="0.2"

    setTimeout(function(){
        document.getElementById("fwrules-update").style.display="unset";
        document.getElementById("loader").style.display="none";
        document.getElementsByClassName("container-fluid")[0].style.opacity="1"
    }, 10000); 
}
