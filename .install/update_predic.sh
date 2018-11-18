#!/bin/bash

# INFO:
# - Folders ~/*custom*/ and ~/lspk will be unchanged
# - Config files are provides with '.example' extension,
#   except if you decide not to keep your config files.

if [ -z $1 ] ; then
    echo usage by indicating a previously downloaded branch in tmp/
    echo "    download_predic.sh master|testing|xxx"
    echo
    exit 0
fi

destino=/home/predic
branch=$1
origen=$destino/tmp/FIRtro-$branch

# Si no se localiza la branch indicada
if [ ! -d $origen ]; then
    echo
    echo ERROR: no se localiza $origen
    echo uso indicando la branch xxx disponible en ~/tmp/pre.di.c-xxx:
    echo "    download_predic.sh master|testing|xxx"
    echo
    exit 0
fi

# Preguntamos si se quieren conservar las configuraciones actuales
conservar="1"
read -r -p "WARNING: will you keep current config? [Y/n] " tmp
if [ "$tmp" = "n" ] || [ "$tmp" = "N" ]; then
    echo All files will be overwritten.
    read -r -p "Are you sure? [y/N] " tmp
    if [ "$tmp" = "y" ] || [ "$tmp" = "Y" ]; then
        conservar=""
    else
        conservar="1"
        echo Will keep current config.
    fi
fi

read -r -p "WARNING: contiue updating? [y/N] " tmp
if [ "$tmp" != "y" ] && [ "$tmp" != "Y" ]; then
    echo Bye.
    exit 0
fi


################################################################################
###                                 INICIO                                   ###
################################################################################

cd $destino

######################################################################
# Preventivo: hacemos respaldos .LAST de lo que hubiera ya configurado
######################################################################
echo "(i) backing up *.LAST for config files"

## carpeta HOME:
cp .mpdconf                 .mpdconf.LAST
cp .brutefir_defaults       .brutefir_defaults.LAST
## carpeta MPLAYER
cp .mplayer/config          .mplayer/config.LAST
cp .mplayer/channels.conf   .mplayer/channels.conf.LAST

## carpeta CONFIG:

cp config/config.yml        config/config.yml.LAST
cp config/DVB-T_state.yml   config/DVB-T_state.yml.LAST
cp config/DVB-T.yml         config/DVB-T.yml.LAST
cp config/inputs.yml        config/inputs.yml.LAST
cp config/scripts           config/scripts.LAST
cp config/state.yml         config/state.yml.LAST

rm -f audio/PEQx*LAST       # por si hubiera anteriores no los replicamos
for file in audio/PEQx* ; do
    mv "$file" "$file.LAST"
done

## carpeta WWW:
# cp www/config/config.ini    tmp/www_config.ini.LAST # en tmp/ pq www/ desaparecerá

#########################################################
# Limpieza
#########################################################
echo "(i) Removing old files"
rm -f CHANGES*
rm -f LICENSE*
rm -f README*
rm -f WIP*
rm -rf bin/ # -f porque pueden haber *.pyc protegidos
rm -r doc/
rm -r www/
rm .brutefir_c*

#########################################################
# Copiamos lo nuevo
#########################################################
echo "(i) Copyong from $origen to $destino"
cp -r $origen/*             $destino/
# y los ocultos se deben explicitar para que se copien:
cp $origen/.mpdconf         $destino/
cp $origen/.brutefir*       $destino/
cp -r $origen/.mplayer*     $destino/

########################################################################
# Si se ha pedido conservar las configuraciones las restauramos:
########################################################################
if [ "$conservar" ]; then
    echo "(i) Restoring user config files"

    # carpeta HOME:
    echo "    ".mpdconf
    mv .mpdconf.LAST                .mpdconf
    echo "    .brutefir_defaults"
    mv .brutefir_defaults.LAST      .brutefir_defaults

    # carpeta MPLAYER
    echo "    ".mplayer/config
    mv .mplayer/config.LAST         .mplayer/config
    echo "    ".mplayer/channels.conf
    mv .mplayer/channels.conf.LAST  .mplayer/channels.conf

    # carpeta WWW
    #echo "    "www/config/config.ini
    #cp tmp/www_config.ini.LAST      www/config/config.ini

    # carpeta CONFIG:
    for file in config/*LAST ; do
        nfile=${file%.LAST}         # elimina .LAST encontrado al final '%'
        echo "    "$nfile
        mv $file $nfile
    done

########################################################################
# Si NO se ha pedido conservar las configuraciones, se sobreescriben:
########################################################################
else

cp config/config.yml        config/config.yml.LAST
cp config/DVB-T_state.yml   config/DVB-T_state.yml.LAST
cp config/DVB-T.yml         config/DVB-T.yml.LAST
cp config/inputs.yml        config/inputs.yml.LAST
cp config/scripts           config/scripts.LAST
cp config/state.yml         config/state.yml.LAST


    # Algunos archivos de configuracion se han proporcionado con extension .example:
    cp config/config.example            config/config
    cp config/DVB-T_state.example       config/DVB-T_state
    cp config/DVB-T.example             config/DVB-T
    cp config/scripts.example           config/scripts
    cp config/state.example             config/state

    #cp www/config/config.ini.example    www/config/config.ini
fi

# Caso especial que se ha tratado en tmp/ lo quitamos de ahí
#mv -f tmp/www_config.ini.LAST    www/config/config.ini.LAST


#########################################################
# restaurando FIFOS
#########################################################
echo "(i) Creando fifos para mplayer"
rm -f *fifo
mkfifo tdt_fifo
mkfifo cdda_fifo

#########################################################
# restaurando brutefir_convolver
#########################################################
echo "(i) Un primer arranque de Brutefir para que genere archivos internos"
brutefir

#########################################################
# restaurando permisos
#########################################################
chmod +x bin/*
chmod +x bin_custom/*
chmod +x bin_custom.example/*
chmod -R 755 www/*
#chmod 666 www/config/config*
cd

#########################################################
# END
#########################################################
# Dejamos una marca indicando la branch contenida
touch ~/bin/README_THIS_IS_"$branch"_BRANCH
echo "as per update_predic.sh" > ~/bin/README_THIS_IS_"$branch"_BRANCH
echo ""
echo "(i) Done."
echo ""


#########################################################
# Website 'pre.di.c'
#########################################################
forig=$origen"/.install/pre.di.c.conf"
fdest="/etc/apache2/sites-available/pre.di.c.conf"
actualizar=1
echo ""
echo "(i) Checking the website 'pre.di.c'"
echo "    /etc/apache2/sites-available/pre.di.c.conf"
echo ""

if [ -f $fdest ]; then
    if ! cmp --quiet $forig $fdest; then
        echo "(i) A new version is available "
        echo "    "$forig"\n"
    else
        echo "(i) No changes on the website\n"
        actualizar=""
    fi
fi
if [ "$actualizar" ]; then
    echo "Notice you need admin privilegies (sudo)"
    echo "( ^C to cancel the website update )\n"
    sudo cp $forig $fdest
    sudo a2ensite pre.di.c.conf
    sudo a2dissite 000-default.conf
    sudo service apache2 reload
fi

