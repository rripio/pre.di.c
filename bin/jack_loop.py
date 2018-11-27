#!/usr/bin/env python3

""" sets up loop ports in JACK
"""

import sys
import jack
import threading

def jack_loop(clientname):
    """ creates a jack loop with given 'clientname' """

    # CREDITS:  https://jackclient-python.readthedocs.io/en/0.4.5/examples.html

    # The instance for our loop
    client = jack.Client(clientname)
    # The threading event to keep this running
    event = threading.Event()

    # This sets the actual loop that copies frames from our capture to our playback ports
    @client.set_process_callback
    def process(frames):
        assert len(client.inports) == len(client.outports)
        assert frames == client.blocksize
        for i, o in zip(client.inports, client.outports):
            o.get_buffer()[:] = i.get_buffer()

    # This is a helper when jack shutdowns
    @client.set_shutdown_callback
    def shutdown(status, reason):
        print('JACK shutdown!')
        print('status:', status)
        print('reason:', reason)

    # Create the ports and activate
    for n in 1, 2:
        client.inports.register(f'input_{n}')
        client.outports.register(f'output_{n}')
    client.activate()

    # This is the keeping trick
    with client:
        print( '(jack_loop) running ' + clientname )
        try:
            event.wait()
        except KeyboardInterrupt:
            print('\nInterrupted by user')

if __name__ == '__main__':
    try:
        jack_loop(sys.argv[1])
    except:
        pass
