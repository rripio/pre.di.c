#!/bin/bash

if [[ $1 == "on" ]]; then
    ~/bin/regleta.py 2 4 on
    echo "on" > ~/.ampli
elif [[ $1 == "off" ]]; then
    ~/bin/regleta.py 2 4 off
    echo "off" > ~/.ampli
fi
~/bin/regleta.py
