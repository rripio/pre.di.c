# Linux and packages

See here: 

    https://github.com/AudioHumLab/FIRtro/wiki/04a-Instalación-de-Linux-y-paquetes-de-SW

Usually it is enough to integrate the user wich will run pre.di.c into convenient groups:

    sudo usermod -a -G cdrom,audio,video,plugdev yourUser

Also check you have the following summary of packages on your linux installation:

```
    alsa-utils
    jackd2
    brutefir
    ecasound ecatools python-ecasound ladspa-sdk fil-plugins
    zita-ajbridge zita-njbridge
    apache2
    mpd mpc
```
