(Download and install scripts from AudioHumLab/FIRtro, adapted to pre.di.c)


## First install:

Download manually a copy of download_predic.sh, an run it:

```
wget https://raw.githubusercontent.com/rripio/pre.di.c/master/.install/download_predic.sh
sh download_predic.sh
rm download_predic.sh
```

At this point, the scripts will be accesible under `~/tmp`

## Maintenance:
 
1- Download the last repo on github:

`sh tmp/download_predic.sh <my_brach>`

where `my_branch` can be 'master' or whatever branch name you want to test

2- Update your system:

`sh tmp/update_predic.sh <my_brach>`

3- Run your new pre.di.c
