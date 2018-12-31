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

destination=$HOME
branch=$1
origin=$destination/tmp/pre.di.c-$branch

# If not found the requested branch
if [ ! -d $origin ]; then
    echo
    echo ERROR: not found $origin
    echo must indicated a branch name available at ~/tmp/pre.di.c-xxx:
    echo "    download_predic.sh master|testing|xxx"
    echo
    exit 0
fi

# Wanna keep current configurations?
keepConfig="1"
read -r -p "WARNING: will you keep current config? [Y/n] " tmp
if [ "$tmp" = "n" ] || [ "$tmp" = "N" ]; then
    echo All files will be overwritten.
    read -r -p "Are you sure? [y/N] " tmp
    if [ "$tmp" = "y" ] || [ "$tmp" = "Y" ]; then
        keepConfig=""
    else
        keepConfig="1"
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

cd "$destination"

# if first install
mkdir bin               >/dev/null 2>&1
mkdir -p pre.di.c/.run  >/dev/null 2>&1

######################################################################
# BACKUP user files to *.LAST to keep current configurations
######################################################################

echo "(i) backing up *.LAST for config files"

## HOME:
cp .asoundrc                .asoundrc.LAST                >/dev/null 2>&1
cp .mpdconf                 .mpdconf.LAST                 >/dev/null 2>&1
cp .brutefir_defaults       .brutefir_defaults.LAST       >/dev/null 2>&1

## MPLAYER
cp .mplayer/config          .mplayer/config.LAST          >/dev/null 2>&1
cp .mplayer/channels.conf   .mplayer/channels.conf.LAST   >/dev/null 2>&1

cd pre.di.c

## CONFIG: 'scripts' file and '*.yml' files
mv config/scripts  config/scripts.LAST >/dev/null 2>&1
for file in config/*.yml ; do
    mv "$file" "$file.LAST"
done

## CONFIG: PEQ template files
rm -f config/PEQx*LAST  >/dev/null 2>&1     # discard previous *LAST if any
for file in config/PEQx* ; do
    mv "$file" "$file.LAST"
done

## SCRIPTS
rm scripts/*LAST        >/dev/null 2>&1     # discard previous *LAST if any
for file in scripts/* ; do
    cp "$file" "$file.LAST" >/dev/null 2>&1
done

## CLIENTS / WWW
# - does not contains config neither user files -

## CLIENTS / BIN
rm clients/bin/*LAST    >/dev/null 2>&1     # discard previous *LAST if any
for file in clients/bin/* ; do
    cp "$file" "$file.LAST" >/dev/null 2>&1
done

## CLIENTS / MACROS
# These are privative files, nothing to do here.

#########################################################
# Cleaning
#########################################################
echo "(i) Removing old files"

cd $destination

rm -f CHANGES*                  >/dev/null 2>&1
rm -f LICENSE*                  >/dev/null 2>&1
rm -f README*                   >/dev/null 2>&1
rm -f WIP*                      >/dev/null 2>&1
rm -rf pre.di.c/bin/            # use -f because maybe protected *.pyc
rm -r  pre.di.c/doc/            >/dev/null 2>&1
rm -r  pre.di.c/clients/www/    >/dev/null 2>&1
rm .brutefir_c*                 >/dev/null 2>&1

#########################################################
# Copying the new stuff
#########################################################
echo "(i) Copying from $origin to $destination"
cp -r $origin/*             $destination/
# hidden files must be explicited each one to be copied
cp    $origin/.mpdconf      $destination/           >/dev/null 2>&1
cp    $origin/.brutefir*    $destination/           >/dev/null 2>&1
cp -r $origin/.mplayer*     $destination/           >/dev/null 2>&1

########################################################################
# If wanted to KEEP CONFIGS, will restore the *LAST copies
########################################################################
if [ "$keepConfig" ]; then

    echo "(i) Restoring user config files"

    # HOME:
    echo "    ".asoundrc
    mv .asoundrc.LAST               .asoundrc               >/dev/null 2>&1

    echo "    ".mpdconf
    mv .mpdconf.LAST                .mpdconf                >/dev/null 2>&1

    echo "    ".brutefir_defaults
    mv .brutefir_defaults.LAST      .brutefir_defaults      >/dev/null 2>&1

    echo "    ".mplayer/config
    mv .mplayer/config.LAST         .mplayer/config         >/dev/null 2>&1
 
    echo "    ".mplayer/channels.conf
    mv .mplayer/channels.conf.LAST  .mplayer/channels.conf  >/dev/null 2>&1

    cd pre.di.c

    # CONFIG ( *LAST will include '*.yml' files as well 'scripts' file )
    for file in config/*LAST ; do
        nfile=${file%.LAST}         # removes trailing .LAST '%'
        echo "    "$nfile
        mv $file $nfile
    done

########################################################################
# If NO KEEPING CONFIG, then overwrite:
########################################################################
else
    cd pre.di.c/config

    # config files are provided with '.example' extension
    cp scripts.example           scripts
    cp state.yml.example         state.yml
    cp config.yml.example        config.yml
    cp inputs.yml.example        inputs.yml
    cp DVB-T_state.yml.example   DVB-T_state.yml  >/dev/null 2>&1
    cp DVB-T.example             DVB-T.yml        >/dev/null 2>&1
    cp istreams.yml.example      istreams.yml.yml >/dev/null 2>&1
fi

cd "$destination"

#########################################################
# restoring brutefir_convolver
#########################################################
echo "(i) A first dry brutefir run in order to generate some internal."
brutefir

#########################################################
# restoring FIFOs
#########################################################
echo "(i) Making fifos for mplayer services"
rm -f pre.di.c/*fifo
mkfifo pre.di.c/dvb_fifo         # DVB-T
mkfifo pre.di.c/cdda_fifo        # CDDA
mkfifo pre.di.c/istreams_fifo    # internet streams

#########################################################
# restoring exec permissions
#########################################################

chmod +x bin/*                          >/dev/null 2>&1
chmod +x pre.di.c/bin/*                 >/dev/null 2>&1
chmod +x pre.di.c/clients/bin/*         >/dev/null 2>&1
chmod +x pre.di.c/scripts/*             >/dev/null 2>&1
chmod +x pre.di.c/clients/macros/[1-9]* >/dev/null 2>&1

#########################################################
# A helping file to identify the current branch under pre.di.c/bin/
#########################################################
touch pre.di.c/bin/THIS_IS_"$branch"_BRANCH
echo "as per update_predic.sh" > pre.di.c/bin/THIS_IS_"$branch"_BRANCH
echo ""
echo "(i) Done."
echo ""

#########################################################
# Updates server side php to work under the user $HOME
#########################################################
sed -i -e '/\$home\ =/c\'"    "'\$home\ =\ \"'"$HOME"'\";' \
          pre.di.c/clients/www/php/functions.php

#########################################################
# And updates the updater script
#########################################################
cp "$origin"/.install/update_predic.sh "$destination"/tmp/

#########################################################
# END
#########################################################


#########################################################
# Apache site
#########################################################
forig=$origin"/.install/apache/pre.di.c.conf"
fdest="/etc/apache2/sites-available/pre.di.c.conf"
updateWeb=1
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
        updateWeb=""
    fi
fi
if [ "$updateWeb" ]; then
    echo "Notice you need admin privilegies (sudo)"
    echo "( ^C to cancel the website update )\n"
    sudo cp $forig $fdest
    sudo a2ensite pre.di.c.conf
    sudo a2dissite 000-default.conf
    sudo service apache2 reload
fi
echo ""
echo "(i) NOTICE:"
echo "    If you install pre.di.c under a home other than '/home/predic'"
echo "    please update accordingly:"
echo "        ""$fdest"
