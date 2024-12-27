# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""Customizable initial values."""

# Equalizer

# Audio controls level clamping.
loudness_ref_variation = 12
tone_variation = 6
balance_variation = 6
# Max allowed digital gain (dB).
gain_max = 0
# Min allowed digital gain (dB).
gain_min = -100


# Folder names
# (Relative to main pre.di.c folder).

config_folder = 'config'
clients_folder = 'clients'
loudspeakers_folder = 'loudspeakers'

# Filenames

config_filename = 'config.yml'
state_filename = 'state.yml'
state_init_filename = 'state_init.yml'
sources_filename = 'sources.yml'
clients_filename = 'clients.yml'
camilladsp_filename = 'camilladsp.yml'
eq_filename = 'eq.yml'

loudspeaker_filename = 'loudspeaker.yml'
drc_filename = 'drc.yml'
