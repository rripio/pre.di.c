# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

# customizable initial values

# equalizer

# audio controls level clamping
loudness_ref_variation = 12
tone_variation = 6
balance_variation = 6
# max allowed digital gain (dB)
gain_max = 0
# min allowed digital gain (dB)
gain_min = -100


# folder names
# relatives to main pre.di.c folder

config_folder = 'config'
clients_folder = 'clients'
loudspeakers_folder = 'loudspeakers'

# filenames

config_filename = 'config.yml'
state_filename = 'state.yml'
state_init_filename = 'state_init.yml'
sources_filename = 'sources.yml'
clients_filename = 'clients.yml'
camilladsp_filename = 'camilladsp.yml'
eq_filename = 'eq.yml'

loudspeaker_filename = 'loudspeaker.yml'
drc_filename = 'drc.yml'
