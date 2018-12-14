<?php

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

    /*  Hidden server side php code.
        PHP will response to the client via the standard php output (echo xxx, readfile(xx), etcetera)
    */

    // Retrieves the running loudspeaker on pre.di.c
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

    // Communicates to the pre.di.c TCP/IP server
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

    // Communicates to the auxiliary tasks pre.di.c's TCP/IP server
    function aux_socket ($cmd) {
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

    ///////////////////////////   MAIN: ///////////////////////////////
    // listen to http request then returns results via standard output
    ///////////////////////////////////////////////////////////////////

    /* http://php.net/manual/en/reserved.variables.request.php
    * PHP server side receives associative arrays, i.e. dictionaries, through by the 
    * GET o PUT methods from the client side HTTPREQUEST (usually javascript).
    * The array is what appears after 'php/functions.php?.......', example:
    *          "GET", "php/functions.php?command=level -15"
    * Here the key 'command' has the value 'level -15'
    */

    // lets read the key 'command'
    $command = $_REQUEST["command"];

    //// SPECIAL commands:

    // Reading config FILES
    if ( $command == "read_inputs_file" ) {
        // notice: readfile() does an 'echo', i.e. it returns the contents to the standard php output
        readfile("/home/predic/config/inputs.yml");
    }
    elseif ( $command == "read_config_file" ) {
        readfile("/home/predic/config/config.yml");
    }
    elseif ( $command == "read_speaker_file" ) {
        $fpath = "/home/predic/loudspeakers/".get_loudspeaker()."/speaker.yml";
        readfile($fpath);
    }

    // AMPLIFIER switching
    elseif ( $command == "amplion" ) {
        // The remote script will store the amplifier state into
        // ~/.ampli so that the web can update it.
        aux_socket('ampli on');
    }
    elseif ( $command == "amplioff" ) {
        aux_socket('ampli off');
    }
    elseif ( $command == "amplistatus" ) {
        readfile("/home/predic/.ampli"); // php cannot acces inside /tmp for securety reasons.
    }

    // PLAYER related commands
    elseif ( substr( $command, 0, 7 ) === "player_" ) {
        echo aux_socket($command);
    }

    // User MACROS commands
    elseif ( $command === "list_macros" ) {
        $macros_array = scandir("/home/predic/macros/");
        echo json_encode( $macros_array );
    }
    elseif ( substr( $command, 0, 6 ) === "macro_" ) {
        echo aux_socket( $command );
    }

    //// Any else will be an STANDARD pre.di.c command, then forwarded to pre.di.c's server
    else {
        echo predic_socket($command);
    }

?>
