# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

import sys

import yaml
import numpy as np

import base


def get_yaml(filepath):
    """returns dictionary from yaml config file"""

    with open(filepath) as configfile:
        config_dict = yaml.safe_load(configfile)

    return config_dict


# dictionaries
#try:
config = get_yaml(base.config_path)
inputs = get_yaml(base.inputs_path)
state = get_yaml(base.state_path)
state_init = get_yaml(base.state_init_path)

# after knowing which speaker config to load, load it
loudspeaker_path = (base.loudspeakers_folder + config['loudspeaker']) 
speaker = get_yaml(loudspeaker_path + '/' + base.speaker_filename)
    
#except Exception:
#    print('\n(getconfigs) Error: some config file failed to load')
#    sys.exit()


# target curves
target_mag_path = loudspeaker_path + '/' + speaker['target_mag_curve']
target_pha_path = loudspeaker_path + '/' + speaker['target_pha_curve']

try:
    target = dict.fromkeys(['mag', 'pha'])
    target['mag'] = np.loadtxt(target_mag_path)
    target['pha'] = np.loadtxt(target_pha_path)
except Exception as e:
    print('Failed to load target files: ', e)
    sys.exit(-1)


# EQ curves
try:
    curves = {
        'frequencies'         : np.loadtxt(base.data_folder
                                    + base.frequencies),
        'loudness_mag_curves' : np.loadtxt(base.data_folder
                                    + base.loudness_mag_curves),
        'loudness_pha_curves' : np.loadtxt(base.data_folder
                                    + base.loudness_pha_curves),
        'treble_mag_curves'   : np.loadtxt(base.data_folder
                                    + base.treble_mag_curves),
        'treble_pha_curves'   : np.loadtxt(base.data_folder
                                    + base.treble_pha_curves),
        'bass_mag_curves'     : np.loadtxt(base.data_folder
                                    + base.bass_mag_curves),
        'bass_pha_curves'     : np.loadtxt(base.data_folder
                                    + base.bass_pha_curves)
        }
except Exception as e:
    print('Failed to load EQ files: ', e)
    sys.exit(-1)


# some processing of data for downstream easyer use
# while retaining upstream ease of writing in config files

# audio ports
# turn string space separated enumerations into a lists
for i in range(len(config['audio_ports'])):
    config['audio_ports'][i]=config['audio_ports'][i].split()

# source ports
# turn string space separated enumerations into a lists
for input in inputs:
    inputs[input]['source_ports']=inputs[input]['source_ports'].split()

