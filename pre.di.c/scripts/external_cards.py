#!/usr/bin/env python3
"""
    Runs external cards resampled in JACK
    
    usage:  external_cards.py   start | stop
"""

import sys
from subprocess import Popen
from getconfigs import config

channels =  '2'

def start():
    
    for card, params in config['external_cards'].items():
        jack_name = card
        alsacard =  params['alsacard']
        resampler = params['resampler']
        quality =   str( params['resamplingQ'] )
        try:
            misc = params['misc_params']
        except:
            misc = ''
        
        cmd = f'{resampler} -d{alsacard} -j{jack_name} -c{channels} -q{quality} {misc}'
        if 'zita' in resampler:
            cmd = cmd.replace("-q", "-Q")

        #print(cmd)
        Popen( cmd.split() ) 

def stop():
    Popen( 'pkill -f zita-a2j'.split() )
    Popen( 'pkill -f zita-j2a'.split() )
    Popen( 'pkill -f alsa_in'.split() )
    Popen( 'pkill -f alsa_out'.split() )

if sys.argv[1:]:
    try:
        option = {
            'start' : start,
            'stop'  : stop
            }[ sys.argv[1] ]()
    except:
        print( f'(external_cards) error {option}' ) 
else:
    print(__doc__)

