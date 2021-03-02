#
# vjoyapi.py
#

import ctypes
import winreg
import os.path
from threading import Timer

# TODO Currently has no capability to send POV switch updates

# vJoy installation registry path
REGPATH  = 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{8E31F76F-74C3-47F1-9550-E041EEDC5FBB}_is1'

AXES = {
    'X':    0x30,
    'Y':    0x31,
    'Z':    0x32,
    'RX':   0x33,
    'RY':   0x34,
    'RZ':   0x35,
    'SL0':  0x36,
    'SL1':  0x37,
    'WHL':  0x38,
}

# Global reference to vJoy library
dll = None


def update(rid:int, action:str, value:int):
    global dll

    # Clamp between accepted values
    value = max(value, 0)
    value = min(value, 127)

    real_value = value
    real_action = action .replace('+','').replace('-','')

    if real_action.isdigit():
        # Buttons
        real_action = int(action)
        real_value = True if value > 0 else False
        dll.SetBtn(real_value, rid, real_action)
    elif real_action in AXES:
        # Check for signed axis
        if '-' in action:
            real_value = 64 - ((value/2) + 1)
        elif '+' in action:
            real_value = 64 + ((value/2) - 1)

        dll.SetAxis(int(real_value) << 8, rid, AXES[real_action])



def init(devices) -> None:
    ''' Initialize vJoy '''
    global dll

    # Load vJoy
    vjoy_install_path = ''
    try:
        vjoy_regkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REGPATH)
        vjoy_install_path = winreg.QueryValueEx(
            vjoy_regkey,
            'InstallLocation'
        )[0]
        winreg.CloseKey(vjoy_regkey)
    except OSError:
        raise Exception('Couldn\'t find vJoy, is vJoy installed?')

    try:
        vjoy_dll_path = os.path.join(
            vjoy_install_path,
            'x64',
            'vJoyInterface.dll'
        )
        dll = ctypes.WinDLL(vjoy_dll_path)
    except:
        raise Exception('Couldn\'t load vJoyInterface.dll')

    if not dll.vJoyEnabled():
        raise Exception('Error: vJoy version 2.x not installed or enabled')

    # Load virtual joystick(s)
    try:
        for a in devices:
            vjd_acquired = dll.AcquireVJD(int(a))
            if not vjd_acquired:
                err = 'Couldn\'t acquire virtual joystick {}, device not free'
                raise Exception(err.format(a))
            else:
                dll.ResetVJD(int(a))
    except:
        raise Exception('Trying to open illegal device')

    # Reset all axes to middle
    for d in devices:
        for x in AXES:
            update(d, x, 64)

    return

def close() -> None:
    ''' Relinguish virtual joysticks '''
    global dll

    dll.RelinquishVJD(1)
    return