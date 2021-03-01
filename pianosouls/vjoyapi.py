#
# vjoyapi.py
#

import ctypes
import winreg
import os.path

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
DPOV = {
    'N':    0,
    'E':    1,
    'S':    2,
    'W':    3,
}

# Global initialized state flag
INITIALIZED = False
# Global reference to vJoy "module"
vJoy = None


def set_axis(value:int, rid:int, axis:str):
    if not INITIALIZED: raise Exception('vJoy not initialized')

    if not (
        all(type(p) is int for p in [value, rid])       and
        type(axis) is str                               and
        1 <= rid <= 16                                and
        axis in AXES
    ):
        raise ValueError('Invalid parameters')

    value = max(value, 1)
    value = min(value, 128)
    vJoy.SetAxis(value << 8, rid, AXES[axis])
    return

def set_button(value:bool, rid:int, button:int):
    if not INITIALIZED: raise Exception('vJoy not initialized')

    if not (
        type(value) is bool                             and
        all(type(p) is int for p in [rid, button])      and
        1 <= rid    <= 16                               and
        1 <= button <= 128
    ):
        raise ValueError('Invalid parameters')

    vJoy.SetBtn(value, rid, button)
    return

def init(devices) -> None:
    global INITIALIZED, vJoy
    if INITIALIZED: return

    # Load vJoy
    vjoy_install_path = ''
    try:
        vjoy_regkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REGPATH)
        vjoy_install_path = winreg.QueryValueEx(
            vjoy_regkey,
            'InstallLocation'
        )[0]
        winreg.CloseKey(vjoy_regkey)

        print('vJoy installation found at', vjoy_install_path)
    except OSError:
        raise Exception('Couldn\'t find vJoy, is vJoy installed?')

    try:
        vjoy_dll_path = os.path.join(
            vjoy_install_path,
            'x64',
            'vJoyInterface.dll'
        )
        vJoy = ctypes.WinDLL(vjoy_dll_path)
        print(
            'vJoy loaded succesfully! (using ver. {})'
            .format(vJoy.GetvJoyVersion())
        )
    except:
        raise Exception('Couldn\'t load vJoyInterface.dll')

    if not vJoy.vJoyEnabled():
        raise Exception('Error: vJoy version 2.x not installed or enabled')

    # Load virtual joystick(s)
    try:
        for a in devices:
            vjd_acquired = vJoy.AcquireVJD(int(a))
            print('Acquired virtual joystick', a)
            if not vjd_acquired:
                err = 'Couldn\'t acquire virtual joystick {}, device not free'
                raise Exception(err.format(a))
            else:
                vJoy.ResetVJD(int(a))
    except:
        raise Exception('Trying to open illegal device')

    INITIALIZED = True
    return

def close() -> None:
    global INITIALIZED, vJoy
    if not INITIALIZED: return

    vJoy.RelinquishVJD(1)

    INITIALIZED = False
    return