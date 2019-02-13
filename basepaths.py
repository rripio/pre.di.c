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

## customizable initial values

# folders
home_folder = '/home/predic/'
main_folder = home_folder + 'pre.di.c/'
bin_folder = main_folder
config_folder = main_folder + 'config/'
clients_folder = main_folder + 'clients/'
loudspeakers_folder = main_folder + 'loudspeakers/'
pids_folder = main_folder + 'run/'

# filenames
server_filename = 'server.py'

config_filename = 'config.yml'
state_filename = 'state.yml'
inputs_filename = 'inputs.yml'
clients_list_filename = 'clients'

speaker_filename = 'speaker.yml'

## program composed values

# paths

server_path = main_folder + server_filename

config_path = config_folder + config_filename
state_path = config_folder + state_filename
inputs_path = config_folder + inputs_filename
clients_list_path = config_folder + clients_list_filename

# we still don't know the loudspeaker name, so speaker_path
# is built downstream
