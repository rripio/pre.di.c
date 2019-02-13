### loudspeakers
Container for specific loudspeaker configuration.

Each loudspeaker set configured goes on its own folder. The name of that folder will be used in the config file to determine which loudspeakers to load.

Some example loudspeakers are provided, in the usual full range (_example_1_way_), two ways (_example_2_way_) and three ways (_example_3_way_) configurations. They are intended to be used as templates for your personal configuration.

#### disclaimer

These examples are given in good faith, as the rest of the program, and I have put my best efforts in having them free of mistakes, but the full responsability for its use lies on you.

You must be aware that an erroneous connection, or a software error, or many other causes, can make your speaker drivers suffer currents that can damage or even destroy them. Please, be cautious, double check all your hardware and software setup and use electrical protections for your drivers (resistor, or capacitors when suitable) in the testing phases of your project.

I assume that you know what you are doing, and I take no responsability for any effect the use of this software may have.

You have been warned.

#### example_1_way

This example can be used as template for a full range setup.

All impulse files provided are deltas that do not make any effective filtering, and are meant to be overwritten with the equalizing impulses of your choice.

The given structure allows for 2 room correction filter sets and 2 speaker equalizer sets, named _mp_ and _lp_, suggesting that having low frequency linear phase correction may be desirable some times, and having minimum phase, low delay filters may be needed some times.

#### example_2_way

This example can be used as template for a two ways speaker setup.

Example crossovers are provided at 3000 hz. There are two set of these, linear phase very sharp filters and minimum phase Linkwitz-Riley fourth order filters, without any added equalization.

The other impulse files provided are deltas that do not make any effective filtering, and are meant to be overwritten with the equalizing impulses of your choice.

The given structure allows for 2 room correction filter sets and 2 speaker equalizer sets, named _mp_ and _lp_, suggesting that having low frequency linear phase correction and crossovers without phase shift may be desirable some times, and having minimum phase, low delay filters may be needed some times.

#### example_3_way

This example can be used as template for a three ways speaker setup.

All that is said on _the example_2_way_ setup applies here, except that the filters supplied have crossover points of 300 and 3000 hz.
