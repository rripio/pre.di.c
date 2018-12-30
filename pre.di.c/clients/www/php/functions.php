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

    /*  This is the hidden server side php code.
        PHP will response to the client via the standard php output, for instance:
            echo $some_varible;
            echo "some_string";
            readfile("some_file_path");
    */

    ///////////////////////////////////////////////////////////////////////
    // PLEASE CONFIGURE HERE THE PROPER $HOME PATH WHERE pre.di.c IS HOSTED
    $home = "/home/predic";
    ///////////////////////////////////////////////////////////////////////

    // Retrieves simple configured items from pre.di.c 'config.yml' file
    function get_config($item) {
        global $home;
        $tmp = "";
        $cfile = fopen($home."/pre.di.c/config/config.yml", "r")
                  or die("Unable to open file!");
        while( !feof($cfile) ) {
            $linea = fgets($cfile);
            $found = strpos( $linea, $item);
            if ( $found !== false ) {
                $tmp = str_replace( "\n", "", $linea);
                $tmp = str_replace( $item, "", $tmp);
                $tmp = str_replace( ":", "", $tmp);
                $tmp = trim($tmp);
            }
        }
        fclose($cfile);
        return $tmp;
    }

    // Communicates to the pre.di.c TCP/IP servers.
    // Notice: server address and port are specified
    //         into 'config/config.yml' for each service,
    //         for instance 'control', 'players' or 'aux'.
    function predic_socket ($service, $cmd) {

        $address = get_config( $service."_address" );
        $port    = intval( get_config( $service."_port" ) );
        
        // Creates a TCP socket
        $socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
        if ($socket === false) {
            echo "socket_create() failed: " . socket_strerror(socket_last_error()) . "\n";
        }
        $result = socket_connect($socket, $address, $port);
        if ($result === false) {
            echo "socket_connect() failed: ($result) " . socket_strerror(socket_last_error($socket)) . "\n";
        }
        // Sends and receive:
        socket_write($socket, $cmd, strlen($cmd));
        $out = socket_read($socket, 4096);
        // Tells the server to close the connection from its end:
        socket_write($socket, "quit", strlen("quit"));
        // Empties the receiving buffer:
        socket_read($socket, 4096);
        // And close this end socket:
        socket_close($socket);
        return $out;
    }

    ///////////////////////////   MAIN: ///////////////////////////////
    // listen to http request then returns results via standard output

    /*  http://php.net/manual/en/reserved.variables.request.php
        PHP server side receives associative arrays, i.e. dictionaries, through by the 
        GET o PUT methods from the client side HTTPREQUEST (usually javascript).
        The array is what appears after 'php/functions.php?.......', example:
                "GET", "php/functions.php?command=level -15"
        Here the key 'command' has the value 'level -15'
        So, lets read the key 'command':
    */
    $command = $_REQUEST["command"];

    // READING CONFIG FILES
    // Notice: readfile() does an 'echo', so it returns the contents to the standard php output
    if ( $command == "read_inputs_file" ) {
        readfile($home."/pre.di.c/config/inputs.yml");
    }
    elseif ( $command == "read_config_file" ) {
        readfile($home."/pre.di.c/config/config.yml");
    }
    elseif ( $command == "read_speaker_file" ) {
        $fpath = $home."/pre.di.c/loudspeakers/".get_config("loudspeaker")."/speaker.yml";
        readfile($fpath);
    }

    // AMPLIFIER switching commands are handled by the 'aux' server
    // Notice: It is expected that the remote script will store the amplifier state
    //         into the file '~/.ampli' so that the web can update it.
    elseif ( $command == "amplion" ) {
        predic_socket( 'aux', 'ampli on');
    }
    elseif ( $command == "amplioff" ) {
        predic_socket( 'aux', 'ampli off');
    }
    elseif ( $command == "amplistatus" ) {
        readfile($home."/.ampli"); // php cannot acces inside /tmp for securety reasons.
    }

    // USER MACROS are handled by the 'aux' server
    elseif ( substr( $command, 0, 6 ) === "macro_" ) {
        echo predic_socket( 'aux', $command );
    }
    elseif ( $command === "list_macros" ) {
        $macros_array = scandir($home."/pre.di.c/clients/macros/");
        echo json_encode( $macros_array );
    }

    // PLAYERS related commands are handled by the 'players' server
    elseif ( substr( $command, 0, 7 ) === "player_" ) {
        // The expected playback control syntax is: 'player_play', 'player_pause', etc
        echo predic_socket( 'players', $command );
    }
    elseif ( substr( $command, 0, 4 ) === "http" ) {
        // A stream url to be played back
        echo predic_socket( 'players', $command );
    }

    // Any else will be an STANDARD pre.di.c CONTROL command, handled by the 'control' server
    else {
        echo predic_socket( 'control', $command );
    }

?>
