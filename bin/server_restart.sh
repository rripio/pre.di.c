#!/bin/bash

# kill the control server
pkill -f "server.py control"

# OjO hay veces que se queda algún proceso escuchando en 9999/tcp,
# por ejemplo alsa_in ¿!?, hay que matarlo para liberar el puerto:
# (i) Sometimes has been seen that some process can keep listening on 9999/tcp,
#     for instance alsa_in ¿!?. Lets kill them in order to release our port:
echo "releasing tcp/9999 ... .. ."
fuser -kv 9999/tcp

# Restarting the control server
echo "restarting: server.py control"
~/pre.di.c/bin/server.py control &
