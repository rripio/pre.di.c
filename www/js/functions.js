/*
 * Para debug podemos printar en la consola del navegador: console.log(miVariable);
 * ***  OJO CONVIENE NO DEJAR NINGUN console.log activo porque gasta recursos
 * ***  y la respuesta de las botoneras se verá afectada.
*/

// Función llamada por los eventos de la peich que ordenan algún cambio a pre.di.c
function predic_cmd(cmd, update=true) {
    // Envia el comando 'cmd' a pre.di.c a través del código PHP del server:
    // https://www.w3schools.com/js/js_ajax_http.asp
    var myREQ = new XMLHttpRequest();
    myREQ.open("GET", "php/functions.php?command=" +  cmd, true);
    myREQ.send();

    // Y actualizamos el nuevo estado en la página
    if (update) {
        get_predic_status();
    }
}

// Controla el ampli
function ampli(mode) {
    var myREQ = new XMLHttpRequest();
    myREQ.open("GET", "php/functions.php?command=ampli" + mode, async=true);
    myREQ.send();
}

// Auxiliar para el autoupdate: actualiza el switch del ampli tras consultarlo al server
// (!) async=false NO es recomendable, pero si no no obtengo la response :-?
function update_ampli_switch() {
    var myREQ = new XMLHttpRequest();
    myREQ.open("GET", "php/functions.php?command=amplistatus", async=false);
    myREQ.send();
    ampliStatus = myREQ.responseText.replace('\n','')
    document.getElementById("onoffSelector").value = ampliStatus;
}

// Inicializa le peich incluyendo su auto-update
function page_initiate() {

    // Completamos los selectore de inputs, XO y DRC
    fills_inputs_selector()
    fills_xo_selector()
    fills_drc_selector()

    // Cabecera de la peich
    document.getElementById("cabecera").innerText = ':: pre.di.c :: ' + get_loudspeaker() + ' ::';

    // Inicializamos la peich con el estado de pre.di.c
    get_predic_status();
    // Esperamos 1 s y  programamos el auto-update como tal, cada 3 s:
    // (OjO la llamada a la función en el setInterval va SIN paréntesis)
    setTimeout( setInterval( get_predic_status, 3000 ), 1000);
}

// Obtiene el estado de pre.di.c hablando con el PHP del server
function get_predic_status() {
    // https://www.w3schools.com/js/js_ajax_http.asp

    // Prepara una instancia HttpRequest
    var myREQ = new XMLHttpRequest();

    // Dispara una acción cuando se haya completado el HttpRequest,
    // nosotros actualizaremos la peich con la respuesta del server.
    myREQ.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            page_update(this.responseText);
        }
    };

    // Ejecuta la transacción HttpRequest
    myREQ.open(method="GET", url="php/functions.php?command=status", async=true);
    myREQ.send();
}

// Vuelca el estado de pre.dic.c en la peich
function page_update(status) {

    // Tabla de LEVEL y BALANCE
    document.getElementById("status_LEV").innerHTML = 'LEVEL: '   + status_decode(status, 'level');
    document.getElementById("status_BAL").innerHTML = 'balance: ' + status_decode(status, 'balance');

    // Texto que acompaña a los botones de Tonos
    document.getElementById("bassInfo").innerText   = 'BASS: '    + status_decode(status, 'bass');
    document.getElementById("trebleInfo").innerText = 'TREB: '    + status_decode(status, 'treble');

    // Elemento seleccionado en los selectores de INPUTS, XO y DRC
    document.getElementById("inputsSelector").value =               status_decode(status, 'input');
    document.getElementById("xoSelector").value     =               status_decode(status, 'XO_set');
    document.getElementById("drcSelector").value    =               status_decode(status, 'DRC_set');

    // Rótulo de los botones MUTE, MONO, LOUDNESS en lowercase si están desactivados
    document.getElementById("buttonMute").innerHTML = OnOff( 'mute', status_decode(status, 'muted') );
    document.getElementById("buttonMono").innerHTML = OnOff( 'mono', status_decode(status, 'mono') );
    document.getElementById("buttonLoud").innerHTML = OnOff( 'loud', status_decode(status, 'loudness_track') );

    // Destacamos los botones que están activados
    if ( status_decode(status, 'muted') == 'true' ) {
        document.getElementById("buttonMute").style.background = "rgb(185, 185, 185)";
        document.getElementById("buttonMute").style.color = "white";
    } else {
        document.getElementById("buttonMute").style.background = "rgb(100, 100, 100)";
        document.getElementById("buttonMute").style.color = "lightgray";
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

    // Actualizamos el switch del ampli
    update_ampli_switch()

}

// Auxiliar ortopédico para pedir ciertos archivos al servidor PHP
// (!) async=false NO es recomendable, pero esto sólo se ejecuta al inicio
//     y de esta forma llega lo que tiene que llegar ;-)
function get_file(fid) {
    var phpCmd   = "";
    var response = "todavia_sin_respuesta";
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

// Averigua el valor de una de las propiedades del chorizo status de pre.di.c
function status_decode(status, prop) {
    var result = "";
    arr = status.split("\n"); // Las parejas 'propiedad:valor' vienen separadas por saltos de línea
    for ( i in arr ) {
        if ( prop == arr[i].split(":")[0] ) {
            result = arr[i].split(":")[1]
        }
    }
    return String(result).trim();
}

// Auxiliar para rotular propiedades como por ejemplo muted:true/false ==> 'MUTE' / 'mute'
function OnOff(prop, truefalse) {
    var label = '';
    label = prop.toLowerCase()
    if ( truefalse == 'true' ) { label = prop.toUpperCase(); }
    return label;
}

// Prepara el selector de entradas
function fills_inputs_selector() {
    var inputs = [];

    // Leemos el contenido de "config/inputs.yml"
    // y a falta de un decodificador YAML, lo analizamos a pedales
    var arr = get_file('inputs').split('\n')
    for ( i in arr) {
        if ( (arr[i].substr(-1)==":") && (arr[i].substr(0,1)!=" ") ) {
            inputs.push( arr[i].slice(0,-1) );
        }
    }

    // Ahora rellenamos el selector de entradas de la peich con las encontradas
    // https://www.w3schools.com/jsref/met_select_add.asp
    var x = document.getElementById("inputsSelector");
    for ( i in inputs) {
        var option = document.createElement("option");
        option.text = inputs[i];
        x.add(option);
    }
}

// Prepara el selector de XO
function fills_xo_selector() {
    var xo_sets = get_speaker_prop_sets('XO');
    var x = document.getElementById("xoSelector");
    for ( i in xo_sets ) {
        var option = document.createElement("option");
        option.text = xo_sets[i];
        x.add(option);
    }
}

// Prepara el selector de DRC
function fills_drc_selector() {
    var drc_sets = get_speaker_prop_sets('DRC');
    var x = document.getElementById("drcSelector");
    for ( i in drc_sets ) {
        var option = document.createElement("option");
        option.text = drc_sets[i];
        x.add(option);
    }
}

// Obtiene el nombre del altavoz
// (nota: ahora php ya lo conoce se lo podríamos preguntar pero esto lo hice antes)
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

// Obtiene la lista con los 'sets:' declarados en una propiedad del altavoz, por ej 'XO:' o 'DRC:'
function get_speaker_prop_sets(prop) {
    var prop_sets = [];
    var yaml = get_file('speaker');

    // yaml es un YAML, lo suyo sería usar un parser pero vamos a hacerlo a manubrio:
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

// Auxiliar para averiguar el nivel de indentación de una linea de código,
// por ejemplo de una linea de un archivo YAML.
function indentLevel(linea) {
    var level = 0;
    for ( i in linea ) {
        if ( linea[i] != ' ' ) { break;}
        level += 1;
    }
    return (level);
}
