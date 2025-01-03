# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""Initial code."""

import os
import sys

import yaml

import baseconfig as base


def get_configs(filepath):
    """Return dictionary from yaml config file."""
    with open(filepath) as configfile:
        config_dict = yaml.safe_load(configfile)

    return config_dict


# paths

# main_folder is the folder this very module is run from.
main_folder = os.path.dirname(__file__)

config_folder = f'{main_folder}/{base.config_folder}'
clients_folder = f'{main_folder}/{base.clients_folder}'
loudspeakers_folder = f'{main_folder}/{base.loudspeakers_folder}'

config_path = f'{config_folder}/{base.config_filename}'
state_path = f'{config_folder}/{base.state_filename}'
state_init_path = f'{config_folder}/{base.state_init_filename}'
sources_path = f'{config_folder}/{base.sources_filename}'
clients_path = f'{config_folder}/{base.clients_filename}'
eq_path = f'{config_folder}/{base.eq_filename}'
camilladsp_path = f'{config_folder}/{base.camilladsp_filename}'

# We still don't know the loudspeaker name, so speaker_path
# is built downstream.


# dictionaries

try:

    config = get_configs(config_path)
    sources = get_configs(sources_path)
    state = get_configs(state_path)
    state_init = get_configs(state_init_path)
    eq = get_configs(eq_path)
    camilladsp = get_configs(camilladsp_path)

    # After knowing which speaker config to load, load it.
    loudspeaker_path = f'{loudspeakers_folder}/{config["loudspeaker"]}'
    speaker = get_configs(loudspeaker_path + '/' + base.loudspeaker_filename)
    drc = get_configs(loudspeaker_path + '/' + base.drc_filename)

except Exception as e:
    print(f'\n(init) Error getting configurations: {e}')
    sys.exit()


# Some processing of data for downstream easyer use
# while retaining upstream ease of writing in config files.

# Audio ports
# Turn string space separated enumerations into lists.
config['audio_ports'] = [port.split() for port in config['audio_ports']]

# source ports
# turn string space separated enumerations into lists
for source in sources:
    sources[source]['source_ports'] = sources[source]['source_ports'].split()
