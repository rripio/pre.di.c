#!/usr/bin/env python3

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
    Script para generar una plantilla .ecs Ecasound Chain Setup "a cero"
    para el módulo PEQ del predic.

    Se usa el plugin 'filter' del paquete fil-plugins de Fons Adriaensen.
    Cada plugin 'filter' disponde de 4 filtros paramétricos mono.

    Uso:
      ecasound_PEQ_template.py  numero_de_filtros  Fs [-w: para salvar en ~/audio]
"""
# v2.0:
# - Plugin LADSPA ya que el LV2 está portado por Nedko y no viene
#   en la distribucion estandar de ubuntu 16.04 LTS
# - La plantilla se genera arrancando una instancia temporal de Ecasound,
#   que genera el formato .ecs
# v2.1:
# - Se solicita número de filtros y Fs.

from os import path as os_path, remove as os_remove, rename as os_rename
import sys
from basepaths import config_folder

# para crear una instancia temporal de Ecasound
from pyeca import *

# --- Secuencia de comandos Python para Ecasound ---
# se puede ver un ejemplo en:
# http://nosignal.fi/ecasound/Documentation/programmers_guide/html_ecidoc/eci_doc.html#htoc29

def aux_do_chain(channel, playbackJackPort, numberOfPlugins):
    """ añadimos una chain que se usará para un canal: input----efectos---output
        la input queda abierta
        la output se conecta al puerto Jack especificado
    """
    # El identificador de nuestro plugin filter fil-plugins:
    #pluginURL = "-elv2:http://nedko.aranaudov.org/soft/filter/2/mono"
    pluginURL = "-eli:1970" # version LADSPA

    # Parámetros globales del plugin (active, gain)
    globalParams = "1,0"
    # Parámetros plantilla de cafa filtro del plugin (active, frec, BW, gain)
    filterParams = "0,10,1,0"
    pluginParams = globalParams + "," + ((filterParams+",")*4)[:-1] # tiene 4 filtros

    e.command("c-add "    + channel)
    e.command("c-select " + channel)
    e.command("ai-add jack")
    e.command("ao-add jack," + playbackJackPort)

    for n in range(numberOfPlugins):
        e.command("cop-add " + pluginURL + "," + pluginParams)

def create_PEQ_ChainSetup(numberOfPlugins, Fs):
    """ definición de nuestro setup (ChainSetup)
        esta función se usa una vez para generar un fichero .ecs con los filtros "a cero"
    """
    # El nombre de nuestra "ChainSetup" en Ecasound
    cs_name = "2xFonsA_4band_dualMono"

    e.command("cs-add " + cs_name)                      # declaramos nuestra ChainSetup
    e.command("cs-set-audio-format f32_le,1," + Fs)     # como usamos plugins MONO será "dual mono"
    aux_do_chain("left",  "brutefir:input-0", numberOfPlugins) # chain de cada canal con N plugins
    aux_do_chain("right", "brutefir:input-1", numberOfPlugins)
    e.command("cs-save-as " + fTmp)                     # salvamos a fichero

if __name__ == '__main__':

    if len(sys.argv) > 1:
        Fs = ""
        numberOfPlugins = 0
        salvar = False
        warnings = []

        for cosa in sys.argv[1:]:
            if cosa.isdigit():
                if (int(cosa) >= 4 and int(cosa) <= 32):
                    numberOfFilters = int(cosa)
                    if numberOfFilters % 4:
                        warnings += ["'numero_de_filtros' debe ser múltiplo de 4 y no mayor que 32"]
                    else:
                        numberOfPlugins = numberOfFilters / 4
                else:
                    if cosa in ["44100","48000","96000"]:
                        Fs = cosa
                    else:
                        warnings += ["'Fs' válidas: 44100 48000 96000"]
            elif cosa == "-w":
                salvar = True

        if not (Fs and numberOfPlugins):
            print(__doc__)
            for cosa in warnings:
                print(" "*4 + cosa)
            print()
            sys.exit()

        fTmp =    config_folder + "tmp.ecs"
        fPlanti = config_folder + "PEQx" + str(numberOfFilters) + "_defeat_" + Fs + ".ecs"

        e = ECA_CONTROL_INTERFACE(0)

        # (!) pyeca arroja mensajes de timeout raros al recibir comandos,
        # aunque todo vaya bien
        # e.command("debug 0") # esto no los quita :-/
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = open("/dev/null", "w")
        sys.stderr = open("/dev/null", "w")

        create_PEQ_ChainSetup(numberOfPlugins, Fs)

        sys.stdout = original_stdout
        sys.stderr = original_stderr

        print()
        print(open(fTmp, "r").read())
        if salvar:
            os_rename(fTmp, fPlanti)
            print("\n(i) guardado en: " + fPlanti + "\n")
        else:
            os_remove(fTmp)
            print("\n(i) indicar -w al final para salvar.\n")
    else:
        print(__doc__)
