
Any file here named like **`N_some_nice_name`** will be consider as an user macro
by the control web page, then a button will be used to trigger the macro.

N determines the position into the web macros key pad.

For example

```
$ ls -1 clients/macros/
1_RNE
2_R.Clasica
6_flat sound
README.md
```

Will show the following key pad layout:

```
    [     RNE     ]  [  R.Clasica  ]  [    --      ]
    [     --      ]  [     --      ]  [ flat sound ]
    [     --      ]  [     --      ]  [    --      ]
```

**NOTICE:** if no macro files `N_xxxx` were defined under `~/clients/macros/` then **NO keypad** will be showed on the control web page.

