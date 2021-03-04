#
# pianosouls.py
# Takes MIDI inputs and, when matching configured criteria, sends gamepad/
# joystick input commands to API
# (C) Taneli Hongisto 2021 https://github.com/tanskudaa
#
# Licensed under GPLv3 https://www.gnu.org/licenses/
#


# TODO TODO Functionality to implement TODO TODO
# MIDI Control Change support


import sys
import os
import time
import importlib
import msvcrt
from optparse import OptionParser

from . import midi
from . import music
from . import config

# Global API module dynamically imported in main()
apimod = None
DEFAULT_API = 'vigemclient'

# Global dictionary with current state for each MIDI channel listening to
CH_STATE = {}
# Global dictionary with bindings per each MIDI channel used
BINDINGS = {}
# All trigger-action bindings stored in the following semi-incoprehensible
# format:
# BINDINGS = {
#     # Channels
#     1: {
#         # Binding       [(Device, Action), (Device, Action), ...]
#         ('C', 'E'):     [(1, 'X'), (2, 'Y')]
#     },
#     2: {
#         ('D', 'F'):     [(1, 'X'), (2, 'Y')]
#     }
# }

# Polling rate in seconds. Enforced to limit CPU usage.
POLLING_RATE = 1/60

# State class for each MIDI channel
class MIDIChannelState:
    def __init__(self):
        self.notes_down     = []
        self.notes_rel      = []
        self.pedal_down     = False
        self.actions_active = []

def update_state(msg) -> None:
    global apimod, CH_STATE, BINDINGS, POLLING_RATE
    if apimod == None: raise Exception('Output API not initialized')

    status, data1, data2 = msg[0][0][0:3]
    ch = (status % 16) + 1

    # I am NOT writing "CH_STATE[ch]." in front of these EVERY SINGLE TIME I
    # need them (every other line), but Python doesn't support pointers
    # so here we are :--) I don't care to look for a handier way to unload
    # these, there's only 4.
    if 128 <= status <= 239 and ch in CH_STATE:
        notes_down      = CH_STATE[ch].notes_down
        notes_rel       = CH_STATE[ch].notes_rel
        pedal_down      = CH_STATE[ch].pedal_down
        actions_active  = CH_STATE[ch].actions_active
    else:
        return

    # Control Change
    if 176 <= status <= 191:
        # Sustain pedal
        if data1 == 64:
            pedal_down = True if data2 >= 64 else False
    # Note on
    elif 144 <= status <= 159:
        if data1 not in notes_down: notes_down.append(data1)
        if data1 in notes_rel:      notes_rel.remove(data1)
    # Note off
    elif 128 <= 143:
        notes_rel.append(data1)

    # Clear released notes if not sustaining
    if not pedal_down:
        for n in notes_rel:
            while n in notes_down:
                notes_down.remove(n)
        notes_rel.clear()

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
                    # Under the if-statement conditions, a "note on" played this
                    # cycle happened in the current trigger; data2 can be used
                    # as the value (velocity) for gamepad state updates
                    if 144 <= status <= 159 and data1 == m: value = data2

        # Check whether currently processing binding needs updating
        press_triggered   = (
            tuple(triggers_down) == trigger and
            value >= 0
        )
        release_triggered = (
            tuple(triggers_down) != trigger and
            any(t is trigger for (t, a) in actions_active)

        )

        for a in actions:
            rid             = a[0]
            action          = a[1]
            action_nosign   = action.replace('+','').replace('-','')

            overlap = False
            for tr, ac in actions_active:
                if action_nosign in ac and not tr == trigger:
                    overlap = True

            # Update press event
            if press_triggered:
                apimod.update(rid, action, int(value))
                # # Add to active actions list
                if not (trigger, action) in actions_active:
                    actions_active.append((trigger, action))
            # Update release event
            elif release_triggered:
                if not overlap: apimod.update(rid, action, 0)
                # # Remove from active actions list
                while (trigger, action) in actions_active:
                    actions_active.remove((trigger, action))

    # Load changed state back into the channel state object
    if 128 <= status <= 239 and ch in CH_STATE:
        CH_STATE[ch].notes_down     = notes_down
        CH_STATE[ch].notes_rel      = notes_rel
        CH_STATE[ch].pedal_down     = pedal_down
        CH_STATE[ch].actions_active = actions_active

    return

def main():
    ''' Entry point for pianosouls '''
    global apimod, CH_STATE, BINDINGS, POLLING_RATE, DEFAULT_API

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

    # Default to ViGEm but check if an API module has been specified
    api_module_name = DEFAULT_API
    if options.api_module != None: api_module_name = options.api_module
    # Try to dynamically import API module
    try:
        apimod = importlib.import_module('.'+api_module_name, 'pianosouls')
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

    # Gather all device ID's specified in config
    using_devices = []
    for bn in BINDINGS.values():    # for bind in bindings:
        for ls in bn.values():      # for list (of actions) in link:
            for ac in ls:           # for action in list:
                if not ac[0] in using_devices: using_devices.append(ac[0])
    # Initialize API and output devices
    try:
        apimod.init(using_devices)
    except Exception as err:
        print(err)
        sys.exit(1)

    # Prompt for and open MIDI device for listening
    if options.midi_device_id == None:
        options.midi_device_id = midi.prompt_device()
    if options.midi_device_id == -1:
        print('No or illegal MIDI input device, exiting')
        sys.exit(0)
    midi.open(options.midi_device_id)

    # Create MIDIChannelState object for each MIDI channel listening to
    for ch in BINDINGS: CH_STATE[ch] = MIDIChannelState()

    # Set polling rate
    if options.polling_rate != None:
        POLLING_RATE = float(1/options.polling_rate)

    # Main loop
    try:
        print(' --- Running - R to reload config - CTRL-C to exit --- ')
        while True:
            if midi.DEV.poll():
                update_state(midi.DEV.read(1))

            # R to reload config on the fly
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'r':
                    BINDINGS = config.read_config(options.config_path)
                    print('Reloaded config', options.config_path)

            time.sleep(POLLING_RATE)
    except KeyboardInterrupt:
        print('Exiting')

    # Care says "Bye-bye"
    midi.close()
    apimod.close()
    sys.exit(0)

if __name__ == '__main__':
    main()
