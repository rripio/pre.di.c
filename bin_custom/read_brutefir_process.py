#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Copyright (c) 2016-2018 Rafael Sánchez
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

"""
    A module intended to read the Brutefir convolver running on pre.di.c

    Four lists are provided:

    .outputsMap:         outputs and its corresponding port in JACK.
    .coeffs:             available coefficients.
    .filters_at_start:   filters and coefficients defined into the brutefir_config file.
    .filters_running:    filters and coefficients in progress.

    Each of the provided coeffs and filters are dictionaries.
"""

# v1: prints out
# - the collection of coefficients available in brutefir
# - the filter / coeff configuration defined in brutefir_config
# - the current filter / coeff configuration that runs in the brutefir process
# v2:
# - prints the brutefir output mapping
# - prints brutefir connections on jack
# v2.1
# - admits coeff "dirac pulse" for unfiltered filter stages.
# v2.1a
# - Stop using nc localhost in favor of brutefir_cli.py
# v2.1b
# - The quotes are removed in the output mapping, and the 'outputsMap' list is renamed for better clarity.
# v2.2
# - The code is simplified
# - Dictionaries are used for coeffs and filters
# - The attenuation of the coeff is included
# - filters includes 'to_output' field attenuation and polarity
# v3.0
# - Adaptation to PRE.DI.C
# TODO: python3


import sys, os
import subprocess
import jack_view_connections as jc
import brutefir_cli

HOME = os.path.expanduser("~")

sys.path.append(HOME + "/bin")

############### PRE.DI.C #################
#from basepaths import loudspeaker_folder
from basepaths import loudspeakers_folder
#from getconfigs import loudspeaker
#from getstatus import fs
import getconfigs
loudspeaker_config, _, _ = getconfigs.get_speaker()
fs = loudspeaker_config['fs']
loudspeaker = getconfigs.get_yaml(HOME+'/config/config.yml')['loudspeaker']
# brutefir_config not anymore under fs folder
#audio_folder = loudspeakers_folder + loudspeaker + "/" +fs
audio_folder = loudspeakers_folder + loudspeaker
brutefir_config = audio_folder + "/brutefir_config"

def read_config():
    """ reads outputsMap, coeffs, filters_at_start
    """
    global outputsMap, coeffs, filters_at_start

    f = open(brutefir_config, 'r')
    lineas = f.readlines()

    # Outputs storage
    outputIniciado = False
    outputsTmp= ''
    outputsMap = []

    # Coeff storage
    coeffIndex = -1
    coeffIniciado = False
    coeffs = []

    # Filters Storage
    filterIndex = -1
    filterIniciado = False
    filters_at_start = []

    # Loops reading lines in brutefir.config
    for linea in lineas:

        #######################
        # OUTPUTs
        #######################
        if linea.startswith("output"):
            outputIniciado = True

        if outputIniciado:
            outputsTmp += linea.strip()
            if "}" in linea: # fin de la lectura de las outputs
                outputIniciado = False
                outputsTmp = outputsTmp.split("ports:")[1].split(";")[0].replace(" ", "")
                outputsTmp = outputsTmp.replace('"', '')
                outputsMap = outputsTmp.split(",")

        #######################
        # COEFFs
        #######################
        if linea.startswith("coeff"):
            coeffIniciado = True
            coeffIndex +=1
            cName = linea.split('"')[1].split('"')[0]

        if coeffIniciado:
            if "filename:" in linea:
                pcm = linea.split('"')[1].split('"')[0].split("/")[-1]
            if "attenuation:" in linea:
                cAtten = linea.split()[-1].replace(';','').strip()
            if "}" in linea:
                try:
                    coeffs.append( {'index':str(coeffIndex), 'name':cName, 'pcm':pcm, 'atten':cAtten} )
                except:
                    coeffs.append( {'index':str(coeffIndex), 'name':cName, 'pcm':pcm, 'atten':'0.0'} )
                coeffIniciado = False


        #######################################
        # FILTERs
        #######################################
        if linea.startswith("filter "):
            filterIniciado = True
            filterIndex +=1
            fName = linea.split('"')[1].split('"')[0]

        if filterIniciado:
            if "coeff:" in linea:
                cName = linea.split(':')[1].strip().replace('"', '').replace(";","")
            if "to_outputs" in linea:
                fAtten = linea.split("/")[-2]
                fPol = linea.split("/")[-1].replace(";","")
            if "}" in linea:
                filters_at_start.append( {'index':filterIndex, 'name':fName, 'coeff':cName} )
                filterIniciado = False


def read_running():
    """ Running filters in Brutefir process
    """
    global filters_running
    filters_running = []
    findex = -1

    ###########################################################
    # Get filters running (query 'lf' to Brutefir)
    ###########################################################
    printado = brutefir_cli.bfcli("lf; quit")

    for linea in printado.split("\n"):
        atten = ''
        pol   = ''
        if ': "' in linea:
            findex += 1
            fname = linea.split('"')[-2]
        if "coeff set:" in linea:
            cset = linea.split(":")[1].split()[0]
        if "to outputs:" in linea:
            # NOTA: Se asume que se sale a una única output.
            #       Podría no ser cierto en configuraciones experimentales que
            #       mezclen vías sobre un mismo canal de la tarjet de sonido
            if linea.strip() <> "to outputs:":
                if linea.count('/') == 2:
                    pol   = linea.split('/')[-1].strip()
                    atten = linea.split('/')[-2].strip()
                else:
                    pol   = '1'
                    atten = linea.split('/')[-1].strip()
            # El caso de las etapas eq y drc que no son salidas finales.
            else:
                pol   = '1'
                atten = '0.0'

            filters_running.append( {'index':str(findex), 'fname':fname, 'cset':cset, 'atten':atten, 'pol':pol} )

    #####################################
    # cross relate filter and  coeffs
    #####################################
    # Tenemos los nombres de los filtros con el número de coeficiente cargado en cada filtro,
    # ahora añadiremos el nombre , el pcm y la atenn del coeficiente.
    for frun in filters_running:
        for coeff in coeffs:
            if frun['cset'] == coeff['index']:
                frun['cname']  = coeff['name']
                frun['cpcm']   = coeff['pcm']
                frun['catten'] = coeff['atten']
        # Completamos campos para posibles filtros con coeff: -1;
        # que no habrán sido detectados en el cruce de arriba 'for coeff in coeffs'
        if int(frun['cset']) < 0:
            frun['cset']    = ''
            frun['cname']   = '-1'
            frun['cpcm']    = '-1'
            frun['catten']  = '0.0'

def main():
    """ prints coeffs, filters_running, outputs map and outputs connected in JACK
    """

    read_config()

    read_running()

    ################################
    print "\n--- Outputs map:"
    ################################
    for output in outputsMap:
        print output

    ################################
    print "\n--- Coeffs available:\n"
    ################################
    print "                             coeff# coeff           coeffAtten pcm_name"
    print "                             ------ -----           ---------- --------"
    for c in coeffs:
        a = '{:+6.2f}'.format( float(c['atten']) )
        print " "*29 + c['index'].rjust(4) +"   "+ c['name'].ljust(16) + a.ljust(11) + c['pcm']

    ################################
    print "\n--- Filters Running:\n"
    ################################
    print "fil# filterName  atten pol   coeff# coeff           coeffAtten pcm_name"
    print "---- ----------  ----- ---   ------ -----           ---------- --------"
    for f in filters_running:
        fa = '{:+6.2f}'.format( float(f['atten']) )
        ca = '{:+6.2f}'.format( float(f['catten']) )
        print f['index'].rjust(4) +" "+ f['fname'].ljust(11) + fa + f['pol'].rjust(4) + \
              f['cset'].rjust(7) +"   "+ f['cname'].ljust(16) + ca.ljust(11) + f['cpcm']

    ################################
    print "\n--- Jack:\n"
    ################################
    for x in jc.jackConns('brutefir'):
        if x[1] == '-c':
            tmp = '-->--'
        if x[1] == '-p':
            tmp = '--<--'
        print x[0].ljust(30) + tmp.ljust(8) + x[2]
    print


if __name__ == "__main__" :

    main()
