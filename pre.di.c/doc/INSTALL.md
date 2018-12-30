(Download and install scripts from AudioHumLab/FIRtro, adapted to pre.di.c)


## First install:

1- Download manually a copy of `download_predic.sh`, an run it:

```
wget https://raw.githubusercontent.com/rripio/pre.di.c/master/.install/download_predic.sh
sh download_predic.sh master
rm download_predic.sh
```

At this point, the install scripts will be accesible under `~/tmp`

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
