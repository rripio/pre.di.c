This repository has been archived.
Development follows at [https://codeberg.org/rripio/pre.di.c](https://codeberg.org/rripio/pre.di.c).

# pre.di.c
A preamp and digital crossover.

## Introduction

### Purpose

This program makes a linux computer equipped with a modern sound card behave as a traditional hi-fi preamp, but able also to make advanced DSP equalization and crossover tasks.

That means that, with a proper soundcard, external sources can be used, be them analog or digital, along with digital libraries or streamed sources.

### History

While first experiments began in 2005, the first operative version, using [_brutefir_](https://torger.se/anders/brutefir.html) as DSP engine and coded in _python2_, was made in 2006, with the name [_FIRtro_](https://github.com/AudioHumLab/FIRtro).

Since then it has slowly evolved with the impulse of dear friends and great hi-fi aficionados, and that lends to this aproximate time sequence credits:

pre.di.c is based on FIRtro [https://github.com/AudioHumLab/FIRtro](https://github.com/AudioHumLab/FIRtro)  
FIRtro copyright (C) 2006-2011 Roberto Ripio  
FIRtro copyright (C) 2011-2016 Alberto Miguélez  
FIRtro copyright (C) 2016-2018 Rafael Sánchez  

With the demise of _python2_ a big rewrite was made by me, and another rewrite came with the advent of a new truly wonderful DSP engine, [_CamillaDSP_](https://github.com/HEnquist/camilladsp), that is now the machine behind pre.di.c.

## Disclaimer

This program is given in good faith. I have put my best efforts in having all of it free from mistakes, but the full responsability for its use lies on you.

You must be aware that an erroneous connection, or a software error, or many other causes, can make your speaker drivers suffer currents that can damage or even destroy them. Please be cautious, double check all your hardware and software setup and use electrical protections for your drivers (resistors, or capacitors when suitable) in the testing phases of your project.

I assume that you know what you are doing, and I take no responsability for any effect the use of this software may have.


