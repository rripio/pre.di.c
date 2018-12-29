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

import os
HOME = os.path.expanduser("~")

## customizable initial values

# folders
main_folder = HOME + '/pre.di.c/'
bin_folder = main_folder + 'bin/'
config_folder = main_folder + 'config/'
scripts_folder = main_folder + 'scripts/'
loudspeakers_folder = main_folder + 'loudspeakers/'
pids_folder = main_folder + '.run/'

# filenames
config_filename = 'config.yml'
state_filename = 'state.yml'
inputs_filename = 'inputs.yml'
channels_filename = 'DVB-T.yml'
media_config_filename = 'media.ini'
mcd_config_filename = 'mcd.ini'
script_list_filename = 'scripts'

speaker_filename = 'speaker.yml'

## program composed values

# paths

config_path = config_folder + config_filename
state_path = config_folder + state_filename
inputs_path = config_folder + inputs_filename
script_list_path = config_folder + script_list_filename

channels_path = config_folder + channels_filename
media_config_path = config_folder + media_config_filename
mcd_config_path = config_folder + mcd_config_filename

# we still don't know the loudspeaker name, so speaker_path
# is built downstream
