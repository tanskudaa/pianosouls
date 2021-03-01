#
# pianosouls.midi
#

import pygame.midi

# Always initialize pygame.midi when imported
pygame.midi.init()
# Global reference to device interacted with
DEV = None

def open(n:int):
    ''' Open MIDI input device for listening to midi.DEV '''
    global DEV
    if DEV == None:
        DEV = pygame.midi.Input(n)
    else:
        raise Warning('MIDI device already open')

def close():
    ''' Close MIDI devices in midi.DEV '''
    global DEV
    if isinstance(DEV, pygame.midi.Input):
        DEV.close()
        DEV = None
    else:
        raise Warning('MIDI device already closed')

def prompt_device() -> int:
    ''' Interactive prompt for MIDI device from all available '''

    # References to all input capable devices stored in the following form:
    # input_devices[on_screen_index] == real_reference_index (or: [n] == i)
    input_devices = {}
    device_count = pygame.midi.get_count()

    # Check available MIDI devices and store reference indeces
    n = 1
    print("MIDI input devices available:")
    for i in range(device_count):
        dev_info = pygame.midi.get_device_info(i)
        # Is input enabled
        if dev_info[2] == 1:
            print(f'{n:6}', dev_info[1].decode(), sep='\t')
            input_devices[n] = i
            n += 1

    device_id = None
    while device_id == None:
        try:
            d = int(input('Select MIDI device to use (Ctrl-C to quit): '))
            if d in input_devices:
                device_id = input_devices[d]
            else:
                raise ValueError('Device index invalid')
        except ValueError:
            print('Not a valid input device!')
        except KeyboardInterrupt:
            print('\nInterrupted by user, exiting...')
            return -1

    return device_id
