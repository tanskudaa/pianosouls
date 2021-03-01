#
# pianosouls
#
# Takes MIDI inputs and, when matching configured criteria, sends gamepad/
# joystick input commands to API
#

import sys
import os
import time
import importlib
from optparse import OptionParser

from . import midi
from . import music
from . import config

OUTPUT_API = None

class MIDIChannelState:
    def __init__(self):
        self.notes_down     = []
        self.notes_rel      = []
        self.pedal_down     = False
        self.actions_active = []

# Global dictionary with current state for each MIDI channel listening to
CH_STATE = {}
# Global dictionary with bindings for each MIDI channel
BINDINGS = {}
# Follows the following format:
# BINDINGS = {
#     # Channels
#     1: {
#         # Binding       [(Device, Action)]
#         ('C', 'E'):     [(1, 'X'), (2, 'Y')]
#     },
#     2: {
#         ('D', 'F'):     [(1, 'X'), (2, 'Y')]
#     }
# }

def update_state(msg) -> None:
    global OUTPUT_API, CH_STATE, BINDINGS

    if OUTPUT_API == None:
        raise Exception('Output API not (successfully) initialized')

    status, data1, data2 = msg[0][0][0:3]
    ch = (status % 16) + 1

    if 128 <= status <= 239 and ch in CH_STATE:
        notes_down      = CH_STATE[ch].notes_down
        notes_rel       = CH_STATE[ch].notes_rel
        pedal_down      = CH_STATE[ch].pedal_down
        actions_active  = CH_STATE[ch].actions_active

    # notes_changed = []

    # Control Change
    if 176 <= status <= 191:
        # Sustain pedal
        if data1 == 64:
            pedal_down = True if data2 >= 64 else False
    # Note on
    elif 144 <= status <= 159:
        if data1 not in notes_down: notes_down.append(data1)
        if data1 in notes_rel:      notes_rel.remove(data1)
        # notes_changed.append(data1)
    # Note off
    elif 128 <= 143:
        notes_rel.append(data1)

    # Clear released notes on pedal up
    if not pedal_down:
        for n in notes_rel:
            while n in notes_down:
                notes_down.remove(n)
                # notes_changed.append(n)
        notes_rel.clear()

    # print(notes_changed)

    # Update output
    # TODO This section needs heavy updating when adding CC functionality
    for trigger, actions in BINDINGS[ch].items():
        triggers_down = []
        value         = -1

        # Notes
        for n in trigger:
            for m in notes_down:
                if n in (music.get_note_name(m), music.get_note_name(m, False)):
                    if n not in triggers_down: triggers_down.append(n)
                    if 144 <= status <= 159 and data1 == m: value = data2

        print(trigger, tuple(triggers_down) == trigger, value)

        # Triggered
        if tuple(triggers_down) == trigger and value >= 0:
            for a in actions:
                rid     = a[0]
                action  = a[1]

                # Button
                if type(action) is int:
                    OUTPUT_API.set_button(True, rid, action)
                # Axis
                elif type(action) is str:
                    if '+' in action:
                        action = action.replace('+','')
                        value = 64 + value*(2/3)
                    elif '-' in action:
                        action = action.replace('-','')
                        value = 64 - value*(2/3)
                    OUTPUT_API.set_axis(int(value), rid, action)
                    if (trigger, action) not in actions_active:
                        actions_active.append((trigger, action))
        
        elif tuple(triggers_down) != trigger:
            for a in actions:
                rid     = a[0]
                action  = a[1]

                # Button
                if type(action) is int:
                    # overlap = False
                    # for tr, ac in actions_active:
                    #     if ac == action and tr != trigger: overlap = True
                    #     break
                    # if not overlap:
                    OUTPUT_API.set_button(False, rid, action)
                    # if (trigger, action) in actions_active:
                    #     actions_active.remove((trigger, action))
                # Axis
                elif type(action) is str:
                    if '+' in action or '-' in action:
                        action = action.replace('+','').replace('-','')
                        value = 64
                    else:
                        value = 0

                    overlap = False
                    for tr, ac in actions_active:
                        if ac == action and tr != trigger: overlap = True
                        break
                    if not overlap:
                        OUTPUT_API.set_axis(int(value), rid, action)
                    if (trigger, action) in actions_active:
                        actions_active.remove((trigger, action))

    if 128 <= status <= 239 and ch in CH_STATE:
        CH_STATE[ch].notes_down     = notes_down
        CH_STATE[ch].notes_rel      = notes_rel
        CH_STATE[ch].pedal_down     = pedal_down
        CH_STATE[ch].actions_active = actions_active

    return

def main():
    global OUTPUT_API, CH_STATE, BINDINGS

    # Parse command line arguments
    opt_parser = OptionParser()
    opt_parser.add_option(
        '--api',
        action = 'store', type = 'string', dest = 'api_module'
    )
    opt_parser.add_option(
        '-c', '--conf', '--config',
        action = 'store', type = 'string', dest = 'config_path'
    )
    opt_parser.add_option(
        '-m', '--midich', '--midichannel',
        action = 'store', type = 'int', dest = 'midi_device_id'
    )
    opt_parser.add_option(
        '-p', '--poll',
        action = 'store', type = 'int', dest = 'polling_rate'
    )
    (options, args) = opt_parser.parse_args()

    # Default to included vJoy API and check if any API module has been specified
    api_module_name = 'vjoyapi'
    if options.api_module != None: api_module_name = options.api_module
    # Try to dynamically import API module
    try:
        OUTPUT_API = importlib.import_module('.'+api_module_name, 'pianosouls')
    except ModuleNotFoundError:
        print('Can\'t find module', api_module_name)
        sys.exit(1)

    # Ensure existing config file
    if options.config_path == None:
        print('Must specify config file')
        sys.exit(1)
    options.config_path = os.path.abspath(options.config_path)
    if not os.path.exists(options.config_path):
        print('Can\'t find file', options.config_path)
        sys.exit(1)
    # Load config
    BINDINGS = config.read_config(options.config_path)

    # Count device ID's specified in config
    using_devices = []
    for bn in BINDINGS.values():    # for bind in bindings:
        for ls in bn.values():      # for list (of actions) in link:
            for ac in ls:           # for action in list:
                if not ac[0] in using_devices: using_devices.append(ac[0])
    # Initialize API and output devices
    try:
        OUTPUT_API.init(using_devices)
    except Exception as err:
        print(err)
        sys.exit(1)

    # Open MIDI device for listening
    if options.midi_device_id == None:
        options.midi_device_id = midi.prompt_device()
    if options.midi_device_id == -1:
        print('No or illegal MIDI input device, exiting')
        sys.exit(0)
    midi.open(options.midi_device_id)

    # Create MIDIChannelState object for each MIDI channel listening to
    for ch in BINDINGS: CH_STATE[ch] = MIDIChannelState()

    # Default to polling rate of 60Hz
    if options.polling_rate == None: options.polling_rate = 60
    sleep_time = float(1/options.polling_rate)

    #
    # Main loop
    #
    try:
        print(' --- Running, CTRL-C to exit --- ')
        while True:
            if midi.DEV.poll():
                update_state(midi.DEV.read(1))

            time.sleep(sleep_time)
    except KeyboardInterrupt:
        print('Exiting')
        pass

    # 85. Care says "Bye-bye"
    midi.close()
    OUTPUT_API.close()
    sys.exit(0)

if __name__ == '__main__':
    main()
