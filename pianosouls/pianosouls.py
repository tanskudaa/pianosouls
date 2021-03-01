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

# Polling rate in seconds
POLLING_RATE = 1/60

class MIDIChannelState:
    def __init__(self):
        self.notes_down     = []
        self.notes_rel      = []
        self.pedal_down     = False
        self.actions_active = []

def update_state(msg) -> None:
    global OUTPUT_API, CH_STATE, BINDINGS, POLLING_RATE

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
        # Look through all notes_down that belong to this trigger and append
        # them to list
        for n in trigger:
            for m in notes_down:
                if n in (music.get_note_name(m), music.get_note_name(m, False)):
                    if n not in triggers_down: triggers_down.append(n)
                    # In these conditions, the note on played this cycle
                    # happened in this trigger; data2 can be used as the value
                    # (velocity) for axis and button updates
                    if 144 <= status <= 159 and data1 == m: value = data2

        # Check whether this binding needs to be updated
        press_triggered   = (
            tuple(triggers_down) == trigger and
            value >= 0
        )
        release_triggered = (
            tuple(triggers_down) != trigger and
            any(t is trigger for (t, a) in actions_active)
        )

        # Debug
        # print(trigger, tuple(triggers_down) == trigger, value)

        # Send updated button and axis states to API
        for a in actions:
            rid     = a[0]
            action  = a[1]

            overlap         = False
            already_pressed = False
            for tr, ac in actions_active:
                if ac == action:
                    already_pressed = True
                    if tr != trigger:
                        overlap = True

            if (type(action) is str) and ('+' in action or '-' in action):
                axis      = action
                real_axis = action.replace('+','').replace('-','')

            # Update press event
            if press_triggered:
                # Button
                if type(action) is int:
                    if already_pressed:
                        OUTPUT_API.set_button(False, rid, action)
                        time.sleep(POLLING_RATE)
                    OUTPUT_API.set_button(True, rid, action)
                # Axis
                else:
                    if   '+' in axis: value = 64 + value*(2/3)
                    elif '-' in axis: value = 64 - value*(2/3)
                    OUTPUT_API.set_axis(int(value), rid, real_axis)
                # Add to active actions list
                if not (trigger, action) in actions_active:
                    actions_active.append((trigger, action))
            # Update release event
            elif release_triggered:
                # Button
                if type(action) is int:
                    if not overlap:
                        OUTPUT_API.set_button(False, rid, action)
                # Axis
                else:
                    if '+' in axis or '-' in axis:
                        value = 64
                    else:
                        value = 0
                    OUTPUT_API.set_axis(value, rid, real_axis)
                # Remove from active actions list
                while (trigger, action) in actions_active:
                    actions_active.remove((trigger, action))


    if 128 <= status <= 239 and ch in CH_STATE:
        CH_STATE[ch].notes_down     = notes_down
        CH_STATE[ch].notes_rel      = notes_rel
        CH_STATE[ch].pedal_down     = pedal_down
        CH_STATE[ch].actions_active = actions_active

    return

def main():
    global OUTPUT_API, CH_STATE, BINDINGS, POLLING_RATE

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

    # Read custom polling rate, default to 60Hz
    if options.polling_rate != None:
        POLLING_RATE = float(1/options.polling_rate)

    #
    # Main loop
    #
    try:
        print(' --- Running, CTRL-C to exit --- ')
        while True:
            if midi.DEV.poll():
                update_state(midi.DEV.read(1))

            time.sleep(POLLING_RATE)
    except KeyboardInterrupt:
        print('Exiting')
        pass

    # 85. Care says "Bye-bye"
    midi.close()
    OUTPUT_API.close()
    sys.exit(0)

if __name__ == '__main__':
    main()
