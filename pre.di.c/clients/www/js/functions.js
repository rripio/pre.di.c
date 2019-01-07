/*
Copyright (c) 2018 Rafael Sánchez
This file is part of pre.di.c
pre.di.c, a preamp and digital crossover
Copyright (C) 2018 Roberto Ripio
pre.di.c is based on FIRtro https://github.com/AudioHumLab/FIRtro
Copyright (c) 2006-2011 Roberto Ripio
Copyright (c) 2011-2016 Alberto Miguélez
Copyright (c) 2016-2018 Rafael Sánchez
pre.di.c is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
pre.di.c is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with pre.di.c.  If not, see https://www.gnu.org/licenses/.
*/

/*
   debug trick: console.log(something);
   NOTICE: remember do not leaving any console.log actives
*/

/* TO REVIEW: At some http request we use sync=false, this is not recommended
              but this way we get the answer.
              Maybe it is better to use onreadystatechange as per in refresh_predic_status()
*/

/////////////   GLOBALS //////////////

ecasound_is_used = check_if_ecasound();     // Boolean indicates if pre.di.c uses Ecasound
auto_update_interval = 1500;                // Auto-update interval millisec
advanced_controls = false;                  // Default for showing advanced controls

// Returns boolen as per 'load_ecasound = true|false' inside 'config/config.yml'
function check_if_ecasound() {
    var config  = get_file('config');
    var lines   = config.split('\n');
    var result  = false
    var line    = ''
    for (i in lines) {
        line = lines[i];
        if ( line.trim().split(':')[0].trim() == 'load_ecasound' ){
            if ( line.trim().split(':')[1].trim().toLowerCase() == 'true' ) {
                result = true;
            }
        }
    }
    return result
}

// Used from buttons to send commands to pre.di.c
function predic_cmd(cmd, update=true) {
    // Sends the command to pre.di.c through by the server's PHP:
    // https://www.w3schools.com/js/js_ajax_http.asp
    var myREQ = new XMLHttpRequest();
    myREQ.open("GET", "php/functions.php?command=" +  cmd, true);
    myREQ.send();

    // Then update the web page
    if (update) {
        refresh_predic_status();
    }
}

//////// TOGGLES ADVANCED CONTROLS ////////
function advanced_toggle() {
    if ( advanced_controls !== true ) {
        advanced_controls = true;
    }
    else {
        advanced_controls = false;
    }
    page_update(status);
}

//////// AMPLIFIER CONTROL ////////

// Switch the amplifier
function ampli(mode) {
    var myREQ = new XMLHttpRequest();
    myREQ.open("GET", "php/functions.php?command=ampli" + mode, async=true);
    myREQ.send();
}

// Queries the amplifier switch remote state
function update_ampli_switch() {
    var myREQ = new XMLHttpRequest();
    var ampliStatus = '';
    myREQ.open("GET", "php/functions.php?command=amplistatus", async=false);
    myREQ.send();
    ampliStatus = myREQ.responseText.replace('\n','')
    document.getElementById("onoffSelector").value = ampliStatus;
}

//////// USER MACROS ////////

// Gets a list of user macros availables under pre.di.c/clients/macros/
function list_macros() {
    var list  = [];
    var list2 = []; // a clean list version
    var myREQ = new XMLHttpRequest();
    myREQ.open("GET", "php/functions.php?command=list_macros", async=false);
    myREQ.send();
    list = JSON.parse( myREQ.responseText );
    // Remove '.' and '..' from the list ...
    if ( list.length > 2 ) {
        list = list.slice(2, );
        // ... and discard any disabled item, i.e. not named as 'N_xxxxx'
        for (i in list) {
            if ( isNumeric( list[i].split('_')[0] ) ) {
                list2.push( list[i] );
            }
        }
        return list2;
    }
    // if no elements, but '.' and '..', then returns an empty list
    else { return [];}
}

// Filling the user's macros buttons
function filling_macro_buttons() {
    var macros = list_macros();
    // If no macros on the list, do nothing, so leaving "display:none" on the buttons keypad div
    if ( macros.length < 1 ) { return; }
    // If any macro found, lets show the macros keypad
    document.getElementById( "custom_buttons").style.display = "block";
    var macro = ''
    for (i in macros) {
        macro = macros[i];
        // Macro files are named this way: 'N_macro_name', so N will serve as button position
        macro_name = macro.slice(2, );
        macro_pos = macro.split('_')[0];
        document.getElementById( "macro_button_" + macro_pos ).innerText = macro_name;
    }
}

// Executes user defined macros
function user_macro(prefix, name) {
    var myREQ = new XMLHttpRequest();
    myREQ.open("GET", "php/functions.php?command=macro_" + prefix + "_" + name, async=true);
    myREQ.send();
}

//////// PLAYER CONTROL ////////

// Controls the player
function playerCtrl(action) {
    var myREQ = new XMLHttpRequest();
    myREQ.open("GET", "php/functions.php?command=player_" + action, async=true);
    myREQ.send();
}

// Updates the player control buttons, hightlights the corresponding button to the playback state
function update_player_controls() {
    var myREQ = new XMLHttpRequest();
    var playerState = '';
    myREQ.open("GET", "php/functions.php?command=player_state", async=false);
    myREQ.send();
    playerState = myREQ.responseText.replace('\n','')
    if        ( playerState == 'stop' ) {
        document.getElementById("buttonStop").style.background  = "rgb(185, 185, 185)";
        document.getElementById("buttonStop").style.color       = "white";
        document.getElementById("buttonPause").style.background = "rgb(100, 100, 100)";
        document.getElementById("buttonPause").style.color      = "lightgray";
        document.getElementById("buttonPlay").style.background  = "rgb(100, 100, 100)";
        document.getElementById("buttonPlay").style.color       = "lightgray";
    } else if ( playerState == 'pause' ){
        document.getElementById("buttonStop").style.background  = "rgb(100, 100, 100)";
        document.getElementById("buttonStop").style.color       = "lightgray";
        document.getElementById("buttonPause").style.background = "rgb(185, 185, 185)";
        document.getElementById("buttonPause").style.color      = "white";
        document.getElementById("buttonPlay").style.background  = "rgb(100, 100, 100)";
        document.getElementById("buttonPlay").style.color       = "lightgray";
    } else if ( playerState == 'play' ) {
        document.getElementById("buttonStop").style.background  = "rgb(100, 100, 100)";
        document.getElementById("buttonStop").style.color       = "lightgray";
        document.getElementById("buttonPause").style.background = "rgb(100, 100, 100)";
        document.getElementById("buttonPause").style.color      = "lightgray";
        document.getElementById("buttonPlay").style.background  = "rgb(185, 185, 185)";
        document.getElementById("buttonPlay").style.color       = "white";
    }
}

// Shows the playing info metadata
function update_player_info() {
    var player      = "-";
    var bitrate     = "-";
    var time_pos    = "-:-:-";
    var time_tot    = "-:-:-";
    var artist      = "-";
    var album       = "-";
    var title       = "-";

    var myREQ = new XMLHttpRequest();
    var tmp = '';
    myREQ.open("GET", "php/functions.php?command=player_get_meta", async=false);
    myREQ.send();
    tmp = myREQ.responseText.replace('\n','');
    if ( ! tmp.includes("failed") && ! tmp.includes("refused") )  {
		dicci = JSON.parse( tmp );
		player      = dicci['player'];
		bitrate     = dicci['bitrate'];
		time_pos    = dicci['time_pos'];
		time_tot    = dicci['time_tot'];
		artist      = dicci['artist'];
		album       = dicci['album'];
		title       = dicci['title'];
	}
    // 'player' info not anymore needed because equals to 'input' value
    // document.getElementById("player").innerText = player + ':';
    document.getElementById("time").innerText       = time_pos + "\n" + time_tot;
    document.getElementById("bitrate").innerText    = bitrate + "\nkbps";
    document.getElementById("artist").innerText     = artist;
    document.getElementById("album").innerText      = album;
    document.getElementById("title").innerText      = title;
}

//////// PAGE MANAGEMENT ////////

// Initializaes the page, then starts the auto-update
function page_initiate() {
    
    // Showing and filling the macro buttons
    filling_macro_buttons();

    // Filling the selectors: inputs, XO, DRC and PEQ
    fills_inputs_selector();
    fills_xo_selector();
    fills_drc_selector();
    if ( ecasound_is_used == true){
        insert_peq_selector();
        fills_peq_selector();  
    }

    // Web header shows the loudspeaker name
    document.getElementById("main_lside").innerText = ':: pre.di.c :: ' + get_loudspeaker() + ' ::';

    // Amplifier_switch_status
    update_ampli_switch();

    // Queries the pre.di.c status and updates the page
    refresh_predic_status();

    // Waits 1 sec, then schedules the auto-update itself:
    // Notice: the function call inside setInterval uses NO brackets)
    setTimeout( setInterval( refresh_predic_status, auto_update_interval ), 1000);
}

// Gets the pre.di.c status and updates the page
function refresh_predic_status() {
    // https://www.w3schools.com/js/js_ajax_http.asp

    var myREQ = new XMLHttpRequest();

    // Will trigger an action when HttpRequest has completed: page_update
    myREQ.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            page_update(this.responseText);
        }
    };

    // the http request:
    myREQ.open(method="GET", url="php/functions.php?command=status", async=true);
    myREQ.send();
}

// Dumps pre.di.c status into the web page
function page_update(status) {

    // Level, balance, tone info
    document.getElementById("levelInfo").innerHTML  =            status_decode(status, 'level');
    document.getElementById("balInfo").innerHTML    = 'BAL: '  + status_decode(status, 'balance');
    document.getElementById("bassInfo").innerText   = 'BASS: ' + status_decode(status, 'bass');
    document.getElementById("trebleInfo").innerText = 'TREB: ' + status_decode(status, 'treble');

    // The selected item on INPUTS, XO, DRC and PEQ
    document.getElementById("inputsSelector").value =            status_decode(status, 'input');
    document.getElementById("xoSelector").value     =            status_decode(status, 'XO_set');
    document.getElementById("drcSelector").value    =            status_decode(status, 'DRC_set');
    if ( ecasound_is_used == true){
        document.getElementById("peqSelector").value    =           status_decode(status, 'PEQ_set');
    }
    // MONO, LOUDNESS buttons text lower case if deactivated
    document.getElementById("buttonMono").innerHTML = UpLow( 'mono', status_decode(status, 'mono') );
    document.getElementById("buttonLoud").innerHTML = UpLow( 'loud', status_decode(status, 'loudness_track') );

    // Highlights activated buttons
    if ( status_decode(status, 'muted') == 'true' ) {
        document.getElementById("buttonMute").style.background = "rgb(185, 185, 185)";
        document.getElementById("buttonMute").style.color = "white";
        document.getElementById("buttonMute").style.fontWeight = "bolder";
    } else {
        document.getElementById("buttonMute").style.background = "rgb(100, 100, 100)";
        document.getElementById("buttonMute").style.color = "lightgray";
        document.getElementById("buttonMute").style.fontWeight = "normal";
    }
    if ( status_decode(status, 'mono') == 'true' ) {
        document.getElementById("buttonMono").style.background = "rgb(185, 185, 185)";
        document.getElementById("buttonMono").style.color = "white";
    } else {
        document.getElementById("buttonMono").style.background = "rgb(100, 100, 100)";
        document.getElementById("buttonMono").style.color = "lightgray";
    }
    if ( status_decode(status, 'loudness_track') == 'true' ) {
        document.getElementById("buttonLoud").style.background = "rgb(185, 185, 185)";
        document.getElementById("buttonLoud").style.color = "white";
    } else {
        document.getElementById("buttonLoud").style.background = "rgb(100, 100, 100)";
        document.getElementById("buttonLoud").style.color = "lightgray";
    }

    // Loudspeaker name (can change in some systems)
    document.getElementById("main_lside").innerText = ':: pre.di.c :: ' + get_loudspeaker() + ' ::';

    // Updates the amplifier switch
    update_ampli_switch()
    
    // Updates metadata player info
    update_player_info()

    // Highlights player controls when activated
    update_player_controls()
    
    // Displays the [url] button if input == 'iradio' or 'istreams'
    if (status_decode(status, 'input') == "iradio" ||
        status_decode(status, 'input') == "istreams") {
        document.getElementById( "url_button").style.display = "inline";
    }
    else {
        document.getElementById( "url_button").style.display = "none";
    }

    // Displays or hides the advanced controls section
    if ( advanced_controls == true ) {
        document.getElementById( "advanced_controls").style.display = "block";
    }
    else {
        document.getElementById( "advanced_controls").style.display = "none";
    }
}

// Getting files from server
function get_file(fid) {
    var phpCmd   = "";
    var response = "still_no_answer";
    if      ( fid == 'inputs' ) {
        phpCmd = 'read_inputs_file';
    }
    else if ( fid == 'config' ) {
        phpCmd = 'read_config_file';
    }
    else if ( fid == 'speaker' ) {
        phpCmd = 'read_speaker_file';
    }
    else {
        return null;
    }
    var myREQ = new XMLHttpRequest();
    myREQ.open(method="GET", url="php/functions.php?command=" + phpCmd, async=false);
    myREQ.send();
    return (myREQ.responseText);
}

// Decodes the value from a pre.di.c parameter inside the pre.di.c status stream
function status_decode(status, prop) {
    var result = "";
    arr = status.split("\n"); // the tuples 'parameter:value' comes separated by line breaks
    for ( i in arr ) {
        if ( prop == arr[i].split(":")[0] ) {
            result = arr[i].split(":")[1]
        }
    }
    return String(result).trim();
}

// To upper-lower case button labels, e.g. mono:true/false ==> 'MONO' / 'mono'
function UpLow(prop, truefalse) {
    var label = '';
    label = prop.toLowerCase()
    if ( truefalse == 'true' ) { label = prop.toUpperCase(); }
    return label;
}

// Fills out the inputs selector
function fills_inputs_selector() {
    var inputs = [];

    // Reads "config/inputs.yml" and custom YAML decoding
    var arr = get_file('inputs').split('\n')
    for ( i in arr) {
        if ( (arr[i].substr(-1)==":") && (arr[i].substr(0,1)!=" ") ) {
            inputs.push( arr[i].slice(0,-1) );
        }
    }

    // Filling the options in the inputs selector
    // https://www.w3schools.com/jsref/met_select_add.asp
    var x = document.getElementById("inputsSelector");
    for ( i in inputs) {
        var option = document.createElement("option");
        option.text = inputs[i];
        x.add(option);
    }    

    // And adds the input 'none' as intended into server_process that will disconnet all inputs
    var option = document.createElement("option");
    option.text = 'none';
    x.add(option);
    
}

// XO selector
function fills_xo_selector() {
    var xo_sets = get_speaker_prop_sets('XO');
    var x = document.getElementById("xoSelector");
    for ( i in xo_sets ) {
        var option = document.createElement("option");
        option.text = xo_sets[i];
        x.add(option);
    }
}

// DRC selector
function fills_drc_selector() {
    var drc_sets = get_speaker_prop_sets('DRC');
    var x = document.getElementById("drcSelector");
    for ( i in drc_sets ) {
        var option = document.createElement("option");
        option.text = drc_sets[i];
        x.add(option);
    }
}

// Inserts the PEQ selector if Ecasound is used
function insert_peq_selector(){

    // defines the selector
    var newSelector = document.createElement("select");
    newSelector.setAttribute("id", "peqSelector");
    newSelector.setAttribute("onchange", "predic_cmd('peq ' + this.value, update=false)" );

    // Appends it
    var element = document.getElementById("span_peq");
    // label it with 'PEQ:' and restore font color from grey to white
    element.innerHTML = 'PEQ:';
    element.appendChild(newSelector);
    document.getElementById("peq").style.color = "white";
}

// PEQ selector
function fills_peq_selector() {
    var peq_sets = get_speaker_prop('PEQ');
    var x = document.getElementById("peqSelector");
    for ( i in peq_sets ) {
        var option = document.createElement("option");
        option.text = peq_sets[i];
        x.add(option);
    }
}

// Gets the current loudspeaker
// (recently the php server knows it, but this was done before)
function get_loudspeaker() {
    var result = '';
    var config = get_file('config');
    var lines = config.split('\n');
    for ( i in lines ) {
        line = lines[i];
        if ( line.trim().split(':')[0] == 'loudspeaker' ){
            result = line.trim().split(':')[1];
        }
    }
    return result;
}

// Gets the sets defined into XO or DRC inside speaker.yml
function get_speaker_prop_sets(prop) {
    var prop_sets = [];
    var yaml = get_file('speaker');

    // custom YAML decoder
    var arr = yaml.split("\n");
    var dentroDeProp = false, dentroDeSets = false, indentOfSets = 0;
    for (i in arr) {
        linea = arr[i];
        if ( linea.trim().replace(' ','') == prop+':') { dentroDeProp = true; };
        if ( dentroDeProp ) {

            if ( linea.indexOf('sets:') != -1 ) {
                dentroDeSets = true;
                indentOfSets = indentLevel(linea);
                continue;
            }

            if ( dentroDeSets && indentLevel(linea) <= indentOfSets ){
                     break;
            }

            if ( dentroDeSets ) {
                setName = linea.split(':')[0].trim()
                prop_sets.push( setName );
            }
        }
    }
    return (prop_sets);
}

// Gets the options from some speaker property, e.g. from PEQ.
function get_speaker_prop(prop) {
    var opcs = [];
    var yaml = get_file('speaker');

    // custom YAML decoder
    var arr = yaml.split("\n");
    var dentroDeProp = false;
    for (i in arr) {
        linea = arr[i];
        if ( linea.slice(0, (prop.length)+1 ) == prop+':') { dentroDeProp = true; };
        if ( dentroDeProp ) {

            tmp = linea.replace( prop + ':', '' );
            tmp = tmp.replace('{', '').replace('}', '');
            fields = tmp.split(',');
            for (i in fields) {
                f = fields[i];
                opc = f.split(':')[0].trim()
                opcs.push( opc );
            }

            if ( indentLevel(linea) <= 1 ){ break; }
        }
    }
    return (opcs);
}

// Aux function that retrieves the indentation level of some code line, useful for YAML decoding.
function indentLevel(linea) {
    var level = 0;
    for ( i in linea ) {
        if ( linea[i] != ' ' ) { break;}
        level += 1;
    }
    return (level);
}

// Auxiliary to check for "numeric" strings
function isNumeric(num){
  return !isNaN(num)
}

// Sends an url to the server, to be played back
function play_url() {
    var url = prompt('Enter url to play:');
    if ( url.slice(0,5) == 'http:' || url.slice(0,6) == 'https:' ) {
        var myREQ = new XMLHttpRequest();
        myREQ.open("GET", "php/functions.php?command=" + url, async=true);
        myREQ.send();
    }
}
