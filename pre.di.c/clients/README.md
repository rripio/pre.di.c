
Must locate here any code to be intended as a **client** or **auxiliary** feature from the point of view of **pre.di.c**, for instance:

- the control web page
- a module to interface with players
- a module to interface with local functions
- user macros
- helper scripts
- etc


You must update your `PYTHONPATH` env variable for instance by editing your **`.profile`** home file:
```
export PYTHONPATH="$PYTHONPATH:$HOME/pre.di.c/bin:$HOME/pre.di.c/clients/bin"
```

