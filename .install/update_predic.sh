#!/bin/bash

# INFO:
# - Folders ~/*custom*/ and ~/loudspeakers will be unchanged
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
origen=$destino/tmp/pre.di.c-$branch

# If not found the requested branch
if [ ! -d $origen ]; then
    echo
    echo ERROR: not found $origen
    echo must indicated a branch name available at ~/tmp/pre.di.c-xxx:
    echo "    download_predic.sh master|testing|xxx"
    echo
    exit 0
fi

# Wanna keep current configurations?
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

read -r -p "WARNING: continue updating? [y/N] " tmp
if [ "$tmp" != "y" ] && [ "$tmp" != "Y" ]; then
    echo Bye.
    exit 0
fi


################################################################################
###                                 MAIN                                     ###
################################################################################

cd $destino

######################################################################
# Prevent: backup .LAST for current configurations
######################################################################
echo "(i) backing up *.LAST for config files"

## folder HOME:
cp .mpdconf                 .mpdconf.LAST                 >/dev/null 2>&1
cp .brutefir_defaults       .brutefir_defaults.LAST       >/dev/null 2>&1

## folder MPLAYER
cp .mplayer/config          .mplayer/config.LAST          >/dev/null 2>&1
cp .mplayer/channels.conf   .mplayer/channels.conf.LAST   >/dev/null 2>&1

## folder CONFIG:
cp config/state.yml         config/state.yml.LAST
cp config/config.yml        config/config.yml.LAST
cp config/inputs.yml        config/inputs.yml.LAST
cp config/scripts           config/scripts.LAST
cp config/DVB-T.yml         config/DVB-T.yml.LAST         >/dev/null 2>&1
cp config/DVB-T_state.yml   config/DVB-T_state.yml.LAST   >/dev/null 2>&1
rm -f config/PEQx*LAST       # discarting previous if any
for file in config/PEQx* ; do
    mv "$file" "$file.LAST"
done

## folder SCRIPTS
for file in scripts/* ; do
    cp "$file" "$file.LAST" >/dev/null 2>&1
done

## folder WWW - Notice config.ini still not in use in current web control page
# cp www/config/config.ini    tmp/www_config.ini.LAST # en tmp/ pq www/ desaparecerá

#########################################################
# Cleaning
#########################################################
echo "(i) Removing old files"
rm -f CHANGES*                                  >/dev/null 2>&1
rm -f LICENSE*                                  >/dev/null 2>&1
rm -f README*                                   >/dev/null 2>&1
rm -f WIP*                                      >/dev/null 2>&1
rm -rf bin/ # -f because maybe protected *.pyc 
rm -r doc/                                      >/dev/null 2>&1
rm -r www/                                      >/dev/null 2>&1
rm .brutefir_c*                                 >/dev/null 2>&1

#########################################################
# Copying the new stuff
#########################################################
echo "(i) Copying from $origen to $destino"
cp -r $origen/*             $destino/
# hidden files must be explicited to copy them
cp $origen/.mpdconf         $destino/           >/dev/null 2>&1
cp $origen/.brutefir*       $destino/           >/dev/null 2>&1
cp -r $origen/.mplayer*     $destino/           >/dev/null 2>&1

########################################################################
# If KEEP:
########################################################################
if [ "$conservar" ]; then
    echo "(i) Restoring user config files"

    # folder HOME:
    echo "    ".mpdconf
    mv .mpdconf.LAST                .mpdconf                >/dev/null 2>&1
    echo "    .brutefir_defaults"
    mv .brutefir_defaults.LAST      .brutefir_defaults      >/dev/null 2>&1

    # folder MPLAYER
    echo "    ".mplayer/config
    mv .mplayer/config.LAST         .mplayer/config         >/dev/null 2>&1
    echo "    ".mplayer/channels.conf
    mv .mplayer/channels.conf.LAST  .mplayer/channels.conf  >/dev/null 2>&1

    # folder WWW
    #echo "    "www/config/config.ini
    #cp tmp/www_config.ini.LAST      www/config/config.ini

    # folder CONFIG:
    for file in config/*LAST ; do
        nfile=${file%.LAST}         # removes .LAST at the end '%'
        echo "    "$nfile
        mv $file $nfile
    done

########################################################################
# If NO KEEP, then overwrite:
########################################################################
else
    # Some config files are provided with '.example' extension
    cp config/state.example             config/state
    cp config/config.example            config/config
    cp config/inputs.example            config/inputs
    cp config/scripts.example           config/scripts
    cp config/DVB-T_state.example       config/DVB-T_state  >/dev/null 2>&1
    cp config/DVB-T.example             config/DVB-T        >/dev/null 2>&1
    #cp www/config/config.ini.example    www/config/config.ini
fi

# Special case copied to tmp/ so lets' move it
#mv -f tmp/www_config.ini.LAST    www/config/config.ini.LAST


#########################################################
# restoring FIFOs
#########################################################
echo "(i) Makinf fifos for mplayer"
rm -f *fifo
mkfifo tdt_fifo
mkfifo cdda_fifo

#########################################################
# restoring brutefir_convolver
#########################################################
echo "(i) A first dry brutefir run in order to generate some internal."
brutefir

#########################################################
# restoring exec permissions under bin*
#########################################################
chmod +x bin/*                  >/dev/null 2>&1
chmod +x bin_custom/*           >/dev/null 2>&1
chmod +x bin_custom.example/*   >/dev/null 2>&1
#chmod -R 644 www/*
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

