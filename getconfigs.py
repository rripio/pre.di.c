# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) 2018-2019 Roberto Ripio
#
# pre.di.c is based on FIRtro https://github.com/AudioHumLab/FIRtro
# Copyright (C) 2006-2011 Roberto Ripio
# Copyright (C) 2011-2016 Alberto Miguélez
# Copyright (C) 2016-2018 Rafael Sánchez
#
# pre.di.c is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pre.di.c is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pre.di.c.  If not, see <https://www.gnu.org/licenses/>.

import sys

import yaml

import init

def get_yaml(filepath):
    """returns dictionary from yaml config file"""

    with open(filepath) as configfile:
        config_dict = yaml.safe_load(configfile)

    return config_dict


def get_speaker(config):
    """returns speaker dictionary from yaml speaker config file"""

    full_path = (
        init.loudspeakers_folder
        + config['loudspeaker']
        + '/' + init.speaker_filename
        )

    with open(full_path) as configfile:
        config_dict = yaml.safe_load(configfile)

    target_mag_path = (
        init.loudspeakers_folder
        + config['loudspeaker']
        + '/'
        + config_dict['target_mag_curve']
        )
    target_pha_path = (
        init.loudspeakers_folder
        + config['loudspeaker']
        + '/'
        + config_dict['target_pha_curve']
        )

    return (config_dict, target_mag_path, target_pha_path)


# dictionaries
try:
    config = get_yaml(init.config_path)
    (speaker, target_mag_path, target_pha_path) = get_speaker(config)
    inputs = get_yaml(init.inputs_path)
    state = get_yaml(init.state_path)
    state_init = get_yaml(init.state_init_path)
except Exception:
    print('\n(getconfigs) Error: some config file failed to load')
    sys.exit()
    
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

