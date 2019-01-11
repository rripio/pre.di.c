(Download and install scripts from AudioHumLab/FIRtro, adapted to pre.di.c)

## Required

You need **Python>=3.6** and all python stuff as indicated in **[/README.md](https://github.com/Rsantct/pre.di.c/blob/master/README.md)**. Relogin when done.

## First pre.di.c install:

1- Under your home folder, download manually a copy of `download_predic.sh`, an run it:

```
wget https://raw.githubusercontent.com/Rsantct/pre.di.c/master/.install/download_predic.sh
sh download_predic.sh master
```

At this point, the install scripts and the whole 'master' repo will be located under `~/tmp` (and also deleted the above downloaded)

2- Install pre.di.c

`sh tmp/update_predic.sh master`

Say **'N'** to keep your current config.

## Maintenance:
 
1- Download the last repo from github:

`sh tmp/download_predic.sh <my_brach>`

where `my_branch` can be 'master' or whatever branch name you want to test

2- Update your system:

`sh tmp/update_predic.sh <my_brach>`

Say **'Y'** to keep your current config.


### The web page

To updating your Apache web server you'll need sudo credentials.

Once done you can check the control web from some LAN computer or smartphone

    http://yourPredicHostname.local

