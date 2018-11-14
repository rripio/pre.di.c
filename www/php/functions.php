<?php

    /*
     * Para depurar https://www.ibm.com/developerworks/library/os-debug/index.html
     * En nuestro caso también podemos hacer aquí echo $miVariable, que será recibida por
     * la función JS que haya hecho la http request en el cliente y printarlo allí en 
     * la consola del navegador con console.log(respuesta).
     */

    /* Este código PHP reside localmente en el server y no es visible desde el navegador.
     * Este PHP sera cargado por Apache (si tiene enabled el php_mod),
     * entonces se ESCUCHARAN HTTP_REQUEST como por ejemplo:
     *     "GET", "php/functions.php?command=level -15"
     * que son generadas por el JS del cliente.
     * 
     * Las RESPUESTAS se devolverán mediante la salida estandar de este código,
     * bien mediante 'echo xxxx' o bien mediante algunas funciones que vuelcan su resultado
     * directamente a la salida estandar, como por ejemplo 'readfile()' -ver abajo-
     */

    // Este script debe conocer el nombre del altavoz running para acceder al path
    // adecuado a la hora de proporcionar un archivo speaker.yml al cliente
    // (he preferido que el código js del cliente no muestre paths del servidor)
    function get_loudspeaker() {
        $tmp = "";
        $cfile = fopen("/home/predic/config/config.yml", "r") 
                  or die("Unable to open file!");
        while( !feof($cfile) ) {
            $linea = fgets($cfile);
            $found = strpos( $linea, "loudspeaker");
            if ( $found !== false ) {
                $tmp = str_replace( "\n", "", $linea);
                $tmp = str_replace( "loudspeaker:", "", $tmp);
                $tmp = trim($tmp);
            }
        }
        fclose($cfile);
        return $tmp;
    }

    // Dialoga con el server TCP/IP de PRE.DI.C
    function predic_socket ($cmd) {
        $service_port = 9999;
        $address = "localhost";
        /* Crear un socket TCP/IP */
        $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
        if ($socket === false) {
            echo "socket_create() fallo: razon: " . socket_strerror(socket_last_error()) . "\n";
        }
        $result = socket_connect($socket, $address, $service_port);
        if ($result === false) {
            echo "socket_connect() fallo.\nRazon: ($result) " . socket_strerror(socket_last_error($socket)) . "\n";
        }
        // Envía el comando y recibe la respuesta
        socket_write($socket, $cmd, strlen($cmd));
        $out = socket_read($socket, 4096);
        // Le dice al server que cierre la conexión en su lado
        socket_write($socket, "quit", strlen("quit"));
        socket_read($socket, 4096);
        /* Finaliza este socket TCP/IP */
        socket_close($socket);
        return $out;
    }

    // Dialoga con el server TCP/IP 'server_local.py' que hace lo que se le pida =|:0
    function local_socket ($cmd) {
        $service_port = 9988;
        $address = "localhost";
        /* Crear un socket TCP/IP */
        $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
        if ($socket === false) {
            echo "socket_create() fallo: razon: " . socket_strerror(socket_last_error()) . "\n";
        }
        $result = socket_connect($socket, $address, $service_port);
        if ($result === false) {
            echo "socket_connect() fallo.\nRazon: ($result) " . socket_strerror(socket_last_error($socket)) . "\n";
        }
        // Envía el comando y recibe la respuesta
        socket_write($socket, $cmd, strlen($cmd));
        $out = socket_read($socket, 4096);
        // Le dice al server que cierre la conexión en su lado
        socket_write($socket, "quit", strlen("quit"));
        socket_read($socket, 4096);
        /* Finaliza este socket TCP/IP */
        socket_close($socket);
        return $out;
    }

    ///////////////////   MAIN: ///////////////////////
    // Procesa el COMMAND recibido en la HTTPREQUEST
    // y devuelve resultados mediante 'echo xxxxx'
    ///////////////////////////////////////////////////
    
    /* http://php.net/manual/en/reserved.variables.request.php
    * PHP server side recibe arrays asociativas, o sea diccionarios, mediante los métodos
    * GET o PUT de las HTTPREQUEST originadas por un código del cliente, en nuestro caso
    * es el JS cargado en el navegador que forma parte de la peich.
    * La array es lo que el cliente pone detrás del interrogante, por ejemplo:
    *          "GET", "php/functions.php?command=level -15"
    * Como es un array, debemos seleccionar la clave que nos interesa:
    */
    $command = $_REQUEST["command"];

    // Comandos especiales:
    if ( $command == "read_inputs_file" ) {
        // OjO readfile proporciona un 'echo' del contenido del archivo, a saco.
        // Es decir: vuelca el contenido del archivo a la salida estandar de php.
        readfile("/home/predic/config/inputs.yml");
    }
    elseif ( $command == "read_config_file" ) {
        readfile("/home/predic/config/config.yml");
    }
    elseif ( $command == "read_speaker_file" ) {
        $fpath = "/home/predic/loudspeakers/".get_loudspeaker()."/speaker.yml";
        readfile($fpath);
    }
    elseif ( $command == "amplion" ) {
        local_socket('/home/predic/bin_custom/ampli.sh on');
    }
    elseif ( $command == "amplioff" ) {
        local_socket('/home/predic/bin_custom/ampli.sh off');
    }

    // Comandos estandar para PRE.DI.C (devolvemos el resultado con el echo)
    else {
        echo predic_socket($command);
    }

?>
