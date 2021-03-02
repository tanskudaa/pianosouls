#
# music.py
# pianosouls python module musical logic and lookup tables
#

import re
from math import floor

# NOTE Base notes (0 semitones from... base note) should never be included
# in these tuples. config.read_config() always adds the implied base note
# based on the chord specified.
# NOTE Pure fifths (7 semitones from base note) should be omitted from any
# chord larger than a triad to make playing less frustating and needleslly
# strict. Conversely, raised or lower fifths (values 6 and 8) should always
# be specified.
CHORD_NAME_TO_RELATION = {
    # Seventh chords
    'augmaj7':  (4, 8, 11),
    'aug7':     (4, 8, 10),
    'm7b5':     (3, 6, 10),
    'dim7':     (3, 6, 9),
    'M7b5':     (4, 6, 10),
    'M7':       (4, 10),
    'maj7':     (4, 11),
    'mmaj7':    (3, 11),
    'm7':       (3, 10),
    # Sixth chords
    # TODO Currently the overlap with minor chord inversion makes these
    # confusing and inconsistent from detection standpoint
    # 'M6':       (4, 9),
    # 'm6':       (3, 9),
    # Triads
    'aug':      (4, 8),
    'dim':      (3, 6),
    'M':        (4, 7),
    'm':        (3, 7),
}

# NOTE Sharps and flats are calculated at runtime and as such are intentionally 
# left out from this table
NOTE_LETTER_TO_ID = {
    'C':    0,
    'D':    2,
    'E':    4,
    'F':    5,
    'G':    7,
    'A':    9,
    'B':    11,
}
# This table is used bi-directionally
NOTE_ID_TO_LETTER = {}
for key, value in NOTE_LETTER_TO_ID.items(): NOTE_ID_TO_LETTER[value] = key

def get_note_id(n:str) -> int:
    ''' Returns any valid musical notes MIDI note id value '''
    # Take out all whitespace for safety
    n = re.sub(r'\s+', '', n)
    # Case-insensitivity
    n = n[0].upper() + n[1:]

    # Check validity
    if not (
        len(n) > 0 and
        n[0] in NOTE_LETTER_TO_ID and
        all(c in ('#', 'b') or c.isdigit() for c in n[1:])
    ):
        return -1

    # Parse note id
    base                = NOTE_LETTER_TO_ID[n[0]]
    semitone_adj        = 0
    octave_str          = ''
    octave_real         = 1
    for i in range(1,len(n)):
        if   n[i] == '#':       semitone_adj += 1
        elif n[i] == 'b':       semitone_adj -= 1
        elif n[i].isdigit():    octave_str += n[i]
    if octave_str.isdigit(): octave_real += int(octave_str)

    note_id = base + (12 * octave_real) + semitone_adj

    return note_id

def get_note_name(n:int, find_octave:bool = True, simple=False) -> str:
    ''' Returns the musical notation for any given MIDI note id value '''
    # NOTE I actually want names for arbitary note values, even if they're not
    # strictly playable or exist, so this next line is commented out
    # if not 21 <= n <= 127: return ''

    # Natural
    if n%12 in NOTE_ID_TO_LETTER:
        note = NOTE_ID_TO_LETTER[n%12]
    # Flat/sharp
    else:
        note = NOTE_ID_TO_LETTER[(n-1)%12] + '#'
        if not simple: note += '/' + NOTE_ID_TO_LETTER[(n+1)%12] + 'b'

    # Octave
    if find_octave:
        octave = floor((n-12)/12)
        note += str(octave)
        if '/' in note:
            note = note[:2] + str(octave) + note[2:]

    return note
