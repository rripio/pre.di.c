#!/usr/bin/env python3

"""sets up alsa_loop ports in jack to be used from ALSA sound
backend players"""

import threading
import predic as pd

# create jack loop for connections
# The jack_loop module will keep the loop alive, so we need to thread it.
#pd.jack_loop('alsa_loop')
jloop = threading.Thread( target = pd.jack_loop, args=('alsa_loop',) )
jloop.start()


