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

destination=/home/predic
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

cd $destination

######################################################################
# Prevent: BACKUP user files to *.LAST for current configurations
######################################################################
echo "(i) backing up *.LAST for config files"

## folder HOME:
cp .mpdconf                 .mpdconf.LAST                 >/dev/null 2>&1
cp .brutefir_defaults       .brutefir_defaults.LAST       >/dev/null 2>&1

## folder MPLAYER
cp .mplayer/config          .mplayer/config.LAST          >/dev/null 2>&1
cp .mplayer/channels.conf   .mplayer/channels.conf.LAST   >/dev/null 2>&1

## folder CONFIG - yml files
for file in config/*.yml ; do
    mv "$file" "$file.LAST"
done

## folder CONFIG - PEQ template files
rm -f config/PEQx*LAST # discarting previous if any
for file in config/PEQx* ; do
    mv "$file" "$file.LAST"
done

## folder SCRIPTS
rm scripts/*LAST
for file in scripts/* ; do
    cp "$file" "$file.LAST" >/dev/null 2>&1
done

## folder CLIENTS/WWW
# - does not contains config nor user files -

## folder CLIENTS/BIN
for file in clients/bin/* ; do
    cp "$file" "$file.LAST" >/dev/null 2>&1
done

## folder CLIENTS/MACROS
# These are privative files, nothing to do here.

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
rm -r clients/www/                              >/dev/null 2>&1
rm .brutefir_c*                                 >/dev/null 2>&1

#########################################################
# Copying the new stuff
#########################################################
echo "(i) Copying from $origin to $destination"
cp -r $origin/*             $destination/
# hidden files must be explicit each one to copy them
cp $origin/.mpdconf         $destination/           >/dev/null 2>&1
cp $origin/.brutefir*       $destination/           >/dev/null 2>&1
cp -r $origin/.mplayer*     $destination/           >/dev/null 2>&1

########################################################################
# If KEEPING CONFIG will restore the *LAST copies
########################################################################
if [ "$keepConfig" ]; then
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

    # folder CONFIG:
    for file in config/*LAST ; do
        nfile=${file%.LAST}         # removes .LAST at the end '%'
        echo "    "$nfile
        mv $file $nfile
    done

########################################################################
# If NO KEEPING CONFIG, then overwrite:
########################################################################
else
    # Some config files are provided with '.example' extension
    cp config/state.example             config/state
    cp config/config.example            config/config
    cp config/inputs.example            config/inputs
    cp config/scripts.example           config/scripts
    cp config/DVB-T_state.example       config/DVB-T_state  >/dev/null 2>&1
    cp config/DVB-T.example             config/DVB-T        >/dev/null 2>&1
fi


#########################################################
# restoring FIFOs
#########################################################
echo "(i) Making fifos for mplayer services: dvb and cdda"
rm -f *fifo
mkfifo dvb_fifo
mkfifo cdda_fifo
mkfifo istreams_fifo

#########################################################
# restoring brutefir_convolver
#########################################################
echo "(i) A first dry brutefir run in order to generate some internal."
brutefir

#########################################################
# restoring exec permissions under bin*
#########################################################
chmod +x bin/*                  >/dev/null 2>&1
chmod +x clients/bin/*          >/dev/null 2>&1
chmod +x bin_custom/*           >/dev/null 2>&1
chmod +x bin_custom.example/*   >/dev/null 2>&1
cd

#########################################################
# END
#########################################################
# helping file to identify the current branch under bin/
touch ~/bin/THIS_IS_"$branch"_BRANCH
echo "as per update_predic.sh" > ~/bin/THIS_IS_"$branch"_BRANCH
echo ""
echo "(i) Done."
echo ""


#########################################################
# Website 'pre.di.c'
#########################################################
forig=$origin"/.install/pre.di.c.conf"
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

#### And update the updater
cp "$origin"/.install/update_predic.sh /home/predic/tmp/
