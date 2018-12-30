#!/bin/bash

####################################################
# CONFIGURE HERE the REPOSITORY to download from
#reposite='https://github.com/rripio'
reposite='https://github.com/rsantct'
####################################################

echo
echo "WARNING: Will download from: [ ""$reposite"" ]"
read -r -p "         Is this OK? [y/N] " tmp
if [ "$tmp" != "y" ] && [ "$tmp" != "Y" ]; then
    echo '(i) Remember to edit tmp/download_predic.sh to point to the desired repo.'
    echo '    Bye.'
    exit 0
fi

if [ -z $1 ] ; then
    echo usage:
    echo "    download_predic.sh  master | another_branch"
    echo
    exit 0
fi
branch=$1

# Prepare temp directory
mkdir $HOME/tmp > /dev/null 2>&1
cd $HOME/tmp

# Removes any existent master.zip or predic directory for this branch:
rm $branch.zip
rm -r pre.di.c-$branch

# Downloads the zip
wget "$reposite"/pre.di.c/archive/"$branch".zip

# Unzip
unzip $branch.zip
rm $branch.zip

######################## (i) ######################## 
# Drops the installing (download and update) scripts into tmp/ to be accesible
cp -f pre.di.c-$branch/.install/*sh .

# And back to home
cd
rm download_predic.sh > /dev/null 2>&1
