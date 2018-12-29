# -*- coding: utf-8 -*-

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) 2018 Roberto Ripio
#
# pre.di.c is based on FIRtro https://github.com/AudioHumLab/FIRtro
# Copyright (c) 2006-2011 Roberto Ripio
# Copyright (c) 2011-2016 Alberto Miguélez
# Copyright (c) 2016-2018 Rafael Sánchez
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

import basepaths as bp


def get_yaml(filepath):
    """ returns dictionary from yaml config file"""

    with open(filepath) as configfile:
        config_dict = yaml.load(configfile)

    return config_dict


def get_speaker():
    """ returns speaker dictionary from yaml speaker config file"""

    # get main config file for getting loudspeaker name
    mainconfig =  get_yaml(bp.config_path)

    full_path = ( bp.loudspeakers_folder
                + mainconfig['loudspeaker']
                + '/' + bp.speaker_filename )

    with open(full_path) as configfile:
        config_dict = yaml.load(configfile)

    target_mag_path = (bp.loudspeakers_folder + mainconfig['loudspeaker']
                        + '/' + config_dict['target_mag_curve'])
    target_pha_path = (bp.loudspeakers_folder + mainconfig['loudspeaker']
                        + '/' + config_dict['target_pha_curve'])

    return (config_dict, target_mag_path, target_pha_path)


# dictionaries
try:
    config = get_yaml(bp.config_path)
    (speaker, target_mag_path, target_pha_path) = get_speaker()
    inputs = get_yaml(bp.inputs_path)
    state = get_yaml(bp.state_path)
    channels = get_yaml(bp.channels_path)
except:
    print('\n(getconfigs.py) Error: some config file failed to load')
    sys.exit()
