# ~/.profile: executed by the command interpreter for login shells.
# This file is not read by bash(1), if ~/.bash_profile or ~/.bash_login
# exists.
# see /usr/share/doc/bash/examples/startup-files for examples.
# the files are located in the bash-doc package.

# the default umask is set in /etc/profile; for setting the umask
# for ssh logins, install and configure the libpam-umask package.
umask 002

# if running bash
if [ -n "$BASH_VERSION" ]; then
    # include .bashrc if it exists
    if [ -f "$HOME/.bashrc" ]; then
	. "$HOME/.bashrc"
    fi
fi

# set PATH so it includes user's private bin if it exists
if [ -d "$HOME/bin" ] ; then
    PATH="$HOME/bin:$PATH"
fi

# Solution for jackd2 and dbus without X session
# http://linux-audio.4202.n7.nabble.com/Solution-for-jackd2-and-dbus-without-X-session-td35904.html
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket

# add pre.di.c folder to python module search path
export PYTHONPATH='/home/predic/pre.di.c'
