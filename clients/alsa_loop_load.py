#!/usr/bin/env python3

"""sets up alsa_loop ports in jack to be used from ALSA sound
backend players"""

from predic import jack_loop

# jack_loop will keep the loop alive
jack_loop('alsa_loop')


