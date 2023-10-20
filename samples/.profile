# add this to your ~/.profile file

## predic

# Solution for jackd2 and dbus without X session
# http://linux-audio.4202.n7.nabble.com/Solution-for-jackd2-and-dbus-without-X-session-td35904.html
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/dbus/system_bus_socket
