#
# config.py
# pianosouls module config file parser
#

import os.path
import re

from . import music

def read_config(path:str) -> dict:
    ''' Read and return pianosouls bindings from specified text file '''
    if not os.path.exists(path): return {}

    bindings = {}
    f = open(path, 'r')

    # Currently using channel and device ID's 1
    midi_ch = 1
    rid     = 1

    for l in f:
        # Don't process empty or commented lines
        l = l.strip()
        if len(l) == 0 or l[0] == ';': continue

        # Discard everything after a comment symbol
        comment_index = l.find(';')
        if comment_index >= 0: l = l[0:comment_index]
        l = l.strip()

        #
        # Device or channel declarations
        #
        if ':' in l:
            # Case-insensitive
            l = l.upper()
            # Remove whitespace and split
            l = re.sub(r'\s+', '', l)
            l = l.split(':')
            if l[1].isdigit():
                # Update device or channel for upcoming lines
                if (
                    l[0] in ('DEV, DEVICE') and
                    int(l[1]) > 0
                ):
                    rid = int(l[1])
                elif (
                    l[0] in ('CH', 'CHANNEL') and
                    1 <= int(l[1]) <= 16
                ):
                    midi_ch = int(l[1])
            continue

        #
        # Trigger-action bind declaration
        #
        # Get the gamepad action
        # NOTE Action validity shouldn't be checked here. Leave it for the
        # output module.
        action = l.split()[-1].upper()
        # Take action out, leaves only triggers
        l = l[0:len(l)-len(action)]
        l = re.sub(r'\s+', '', l)

        # Check that there IS information left to parse, ie. there's more than
        # one set of characters in l
        if len(l) == 0: continue

        # Split triggers py comma
        l = l.split(',')
        # Lone comma without specified trigger - don't continue processing
        if '' in l: continue

        # Home stretch
        line_valid = True
        real_trigger = []
        for tr in l:
            #
            # Control Change
            #
            if tr[0:2] == 'CC':
                # TODO Implement Control Change functionality some day
                continue

            #
            # Musical notation
            #
            # Parse raw info about root note
            chord_func_index    = len(tr)
            is_general          = True
            for i in range(1, len(tr)):
                # Check if note has an octave marking
                if tr[i].isdigit(): is_general = False
                # Update chord function starting index
                if not (tr[i] in ('#', 'b') or tr[i].isdigit()):
                    chord_func_index = i
                    break

            note_id = music.get_note_id(tr[0:chord_func_index])
            chord_func = tr[chord_func_index:]
            # Check the validity of all the note/chord info
            if (
                # get_note_id() checks root note validity
                note_id == -1 or
                # if a chord function is defined but...
                (chord_func != '' and
                # a) it isn't listed in valid chord names
                (not chord_func in music.CHORD_NAME_TO_RELATION or
                # b) a chord has an octave marking
                is_general == False))
            ):
                # print('not cool!')
                line_valid = False
                continue

            # Get the individual notes of a chord
            notes_indiv = []
            if chord_func != '':
                root_note = tr[0:chord_func_index]
                notes_indiv.append(music.get_note_id(root_note))
                relations = music.CHORD_NAME_TO_RELATION[chord_func]
                for r in relations:
                    notes_indiv.append(note_id + r)
            else:
                notes_indiv.append(music.get_note_id(tr))

            # Ensure unique naming for enharmonically same notes
            for n in notes_indiv:
                name_unique = None
                if is_general:
                    name_unique = music.get_note_name(n, False)
                else:
                    name_unique = music.get_note_name(n, True)

                real_trigger.append(name_unique)

        # Green light
        if line_valid:
            real_trigger = tuple(real_trigger)

            if not midi_ch in bindings:
                bindings[midi_ch] = {}
            if not real_trigger in bindings[midi_ch]:
                bindings[midi_ch][real_trigger] = []

            bindings[midi_ch][real_trigger].append((rid, action))

    f.close()
    return bindings
