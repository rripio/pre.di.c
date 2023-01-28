# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

import os
import sys

import yaml
import numpy as np

import baseconfig as base


def get_yaml(filepath):
    """returns dictionary from yaml config file"""

    with open(filepath) as configfile:
        config_dict = yaml.safe_load(configfile)

    return config_dict


# paths

# main folder is the folder this very module is run from
main_folder = os.path.dirname(__file__)

config_folder = f'{main_folder}/{base.config_folder}'
clients_folder = f'{main_folder}/{base.clients_folder}'
loudspeakers_folder= f'{main_folder}/{base.loudspeakers_folder}'

config_path= f'{config_folder}/{base.config_filename}'
state_path = f'{config_folder}/{base.state_filename}'
state_init_path = f'{config_folder}/{base.state_init_filename}'
sources_path = f'{config_folder}/{base.sources_filename}'
clients_path = f'{config_folder}/{base.clients_filename}'
eq_path = f'{config_folder}/{base.eq_filename}'
camilladsp_path = f'{config_folder}/{base.camilladsp_filename}'

# we still don't know the loudspeaker name, so speaker_path \
# is built downstream


# dictionaries

try:

    config = get_yaml(config_path)
    sources = get_yaml(sources_path)
    state = get_yaml(state_path)
    state_init = get_yaml(state_init_path)
    eq = get_yaml(eq_path)

    # after knowing which speaker config to load, load it
    loudspeaker_path = f'{loudspeakers_folder}/{config["loudspeaker"]}' 
    speaker = get_yaml(loudspeaker_path + '/' + base.loudspeaker_filename)
    drc = get_yaml(loudspeaker_path + '/' + base.drc_filename)

except Exception as e:
   print(f'\nError getting configurations: {e}')
   sys.exit()


# some processing of data for downstream easyer use
# while retaining upstream ease of writing in config files

# audio ports
# turn string space separated enumerations into a lists
for i in range(len(config['audio_ports'])):
    config['audio_ports'][i]=config['audio_ports'][i].split()

# source ports
# turn string space separated enumerations into a lists
for source in sources:
    sources[source]['source_ports']=sources[source]['source_ports'].split()

