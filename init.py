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

import numpy as np
import yaml

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
except Exception:
    print('Failed to load target files')
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

