#!/bin/bash

killall qjackctl
sleep 3
while true; do
    if [[ $(jack_lsp) == *"system"* ]]; then
        break
    fi
    # echo "ESPERANDO A JACK"
    sleep .25
done

qjackctl &

exit 0

while true; do
    echo "----------------"
    jack_lsp
    sleep .5
done
