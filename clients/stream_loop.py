#! /home/predic/camilladsp/.venv/bin/python

# This file is part of pre.di.c
# pre.di.c, a preamp and digital crossover
# Copyright (C) Roberto Ripio

"""Set up loop ports in jack."""

import multiprocessing as mp

import jack


def jack_loop(clientname):
    """Create a jack loop with given 'clientname'."""
    # CREDITS:
    # https://jackclient-python.readthedocs.io/en/0.4.5/examples.html

    # the jack module instance for our looping ports
    client = jack.Client(name=clientname, no_start_server=True)

    if client.status.name_not_unique:
        client.close()
        print(f'\n(lib) \'{clientname}\''
              'already exists in JACK, nothing done.')
        return

    # will use the multiprocessing.Event mechanism to keep this alive
    event = mp.Event()

    # this sets the actual loop that copies frames from our capture \
    # to our playback ports
    @client.set_process_callback
    def process(frames):
        assert len(client.inports) == len(client.outports)
        assert frames == client.blocksize
        for i, o in zip(client.inports, client.outports):
            o.get_buffer()[:] = i.get_buffer()

    # if jack shutdowns, will trigger on 'event' so that the below \
    # 'whith client' will break.
    @client.set_shutdown_callback
    def shutdown(status, reason):
        print('\n(lib) JACK shutdown!')
        print('(lib) JACK status:', status)
        print('(lib) JACK reason:', reason)
        # this triggers an event so that the below 'with client' \
        # will terminate
        event.set()

    # create the ports
    for n in (1, 2):
        client.inports.register(f'input_{n}')
        client.outports.register(f'output_{n}')
    # client.activate() not needed, see below

    # this is the keeping trick
    with client:
        # when entering this with-statement, client.activate() is called
        # this tells the JACK server that we are ready to roll
        # our above process() callback will start running now

        print(f'\n(lib) running {clientname}')
        try:
            event.wait()
        except KeyboardInterrupt:
            print('\n(lib) Interrupted by user')
        except Exception as e:
            print('\n(lib) Terminated: ', e)


# create jack loop for connections
# The jack_loop module will keep the loop alive, so we need to thread it.
jloop = mp.Process(target=jack_loop, args=('stream_loop',))
jloop.start()
