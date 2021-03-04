#
# vigemclient.py
#

import os
from ctypes import *
from threading import Timer

# Global ViGEm DLL (module) reference
dll = None
# Global ViGEm client pointer
client = None
# Global dictionary with id's pointing to ViGEm controller pointers
pads = {}
# Global dictionary with each controller's current state stored
pad_states = {}

# Interval in seconds at which buttons are de-pressed and then re-pressed
BUTTON_REPRESS_RATE = 1/30

BUTTONS = {
    'UP':       0x0001,
    'DOWN':     0x0002,
    'LEFT':     0x0004,
    'RIGHT':    0x0008,
    'START':    0x0010,
    'BACK':     0x0020,
    'LS':       0x0040,
    'RS':       0x0080,
    'LB':       0x0100,
    'RB':       0x0200,
    'GUIDE':    0x0400,
    'A':        0x1000,
    'B':        0x2000,
    'X':        0x4000,
    'Y':        0x8000
}
AXES = [
    'LX',
    'LY',
    'RX',
    'RY'
]
TRIGGERS = [
    'LT',
    'RT'
]

# Gamepad state class
class XUSB_REPORT(Structure):
    _fields_ = [
        ('wButtons', c_ushort),
        ('bLeftTrigger', c_byte),   # 0-128
        ('bRightTrigger', c_byte),
        ('sThumbLX', c_short),      # (0-128) << 8
        ('sThumbLY', c_short),      
        ('sThumbRX', c_short),
        ('sThumbRY', c_short)
    ]

def update(rid:int, action:str, value:int):
    ''' Update the state of the ViGEm gamepad '''
    global dll, pads, pad_states, BUTTON_REPRESS_RATE

    # Compensate for piano velocity
    # NOTE Shaky
    value = int(value * (3/2))
    # Clamp between accepted values
    value = max(value, 0)
    value = min(value, 127)

    # Check if signed axis
    if '-' in action: value = (-value) - 1
    real_action = action.replace('+','').replace('-','')

    if real_action in BUTTONS:
        is_pressed = pad_states[rid].wButtons & BUTTONS[real_action] != 0
        if value > 0 and is_pressed:
            # TODO Scary multithreading, I'm certain this breaks everything
            # in a way I could never have imagined but hey life's short
            Timer(BUTTON_REPRESS_RATE, update, (rid, real_action, value)).start()
        pad_states[rid].wButtons ^= BUTTONS[real_action]
    elif real_action in TRIGGERS:
        if real_action == 'LT':
            pad_states[rid].bLeftTrigger = value
        else:
            pad_states[rid].bRightTrigger = value
    elif real_action in AXES:
        if   real_action == 'LX':
            pad_states[rid].sThumbLX = value << 8
        elif real_action == 'LY':
            pad_states[rid].sThumbLY = value << 8
        elif real_action == 'RX':
            pad_states[rid].sThumbRX = value << 8
        elif real_action == 'RY':
            pad_states[rid].sThumbRY = value << 8

    dll.vigem_target_x360_update(client, pads[rid], pad_states[rid])

def init(devices):
    ''' Initialize ViGEm gamepads '''
    global dll, client, pads

    home = os.path.join(os.path.abspath(__file__), '..')
    dll = WinDLL(os.path.join(home, 'ViGEMClient.dll'))
    # TODO try-except file not found

    dll.vigem_alloc.restype = POINTER(c_void_p)
    dll.vigem_connect.restype = c_uint
    dll.vigem_target_x360_alloc.restype = POINTER(c_void_p)
    dll.vigem_target_add.restype = c_uint

    client = dll.vigem_alloc()
    retval = dll.vigem_connect(client)
    # TODO retval error value check, has to be 0x20000000

    for d in devices:
        pads[d] = dll.vigem_target_x360_alloc()
        pir = dll.vigem_target_add(client, pads[d])
        # TODO pir error value check, has to be 0x20000000

        # TODO Can't you initialize this in the struct
        pad_states[d] = XUSB_REPORT(0, 0, 0, 0, 0, 0, 0)

def close():
    ''' Close and free ViGEm gamepad allocations '''
    global dll, client, pads

    for p in pads.values():
        dll.vigem_target_remove(client, p)
        dll.vigem_target_free(p)

    dll.vigem_disconnect(client)
    dll.vigem_free(client)
