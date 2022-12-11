# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

import os
import sys

import numpy as np


## customizable initial values

# folders
# main folder is the folder this very module is run from
# allways put a slash after a folder name

main_folder = os.path.dirname(__file__) + '/'
bin_folder = main_folder
config_folder = main_folder + 'config/'
data_folder = main_folder + 'data/'
clients_folder = main_folder + 'clients/'
loudspeakers_folder = main_folder + 'loudspeakers/'
pids_folder = main_folder + 'run/'

# filenames
config_filename = 'config.yml'
state_filename = 'state.yml'
state_init_filename = 'state_init.yml'
inputs_filename = 'inputs.yml'
clients_filename = 'clients.yml'
speaker_filename = 'speaker.yml'


## program composed values

# paths
config_path = config_folder + config_filename
state_path = config_folder + state_filename
state_init_path = config_folder + state_init_filename
inputs_path = config_folder + inputs_filename
clients_path = config_folder + clients_filename


## equalizer

# jump between equalization curves is 1dB
# all values of bass, treble and loudness are rounded to the closer integer

# filenames
frequencies = 'R20_ext-freq.dat'
loudness_mag_curves = 'R20_ext-loudness_mag.dat'
loudness_pha_curves = 'R20_ext-loudness_pha.dat'
treble_mag_curves = 'R20_ext-treble_mag.dat'
treble_pha_curves = 'R20_ext-treble_pha.dat'
bass_mag_curves = 'R20_ext-bass_mag.dat'
bass_pha_curves = 'R20_ext-bass_pha.dat'

# parameters

# loudness curves references
loudness_SPLref = 83
loudness_SPLmax = 90
loudness_SPLmin = 70
# audio controls level clamping
loudness_ref_variation = 12
tone_variation = 6
balance_variation = 6
# max allowed digital gain (dB)
gain_max = 0
# min allowed digital gain (dB)
gain_min = -100

# we still don't know the loudspeaker name, so speaker_path \
# is built downstream
