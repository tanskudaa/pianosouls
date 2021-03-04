# pianosouls
Emulate gamepad input with any MIDI capable instrument

## About
pianosouls is a python application that interprets MIDI data from any MIDI input capable device and transforms it into virtual gamepad inputs. In short, it let's you play any video game with any MIDI capable digital instrument.

Some examples include:
  - Playing Dark Souls by jamming to the Firelink Shrine theme on a digital piano
  - Transforming a drum machine or sampler into a fighting stick
  - Transforming your digital piano into four distinct gamepads for split-screen multiplayer
  - Anything you can imagine

pianosouls supports inputs from all 16 MIDI channels and, in theory, any arbitary number of virtual gamepads. Configuration supports musical notation and the application detects chords when they are played.

MIDI Control Change functionality has not yet been implemented but is work in progress. This means sliders and knobs aren't yet registered by pianosouls, which makes the program not ideal for simulator games at it's current state.

Heavily inspired and influenced by [c0redumb's](https://github.com/c0redumb) [midi2vjoy](https://github.com/c0redumb/midi2vjoy) script - I initially planned on forking that project but ended up writing everything from scratch. Huge thanks - I would have had no clue where to even start without stumbling upon your code.

## Installation
```ViGEmBus``` and ```Python``` are required to run pianosouls.

  1. Python is used to run the application and can be downloaded and installed from https://www.python.org/. The latest version is recommended.
  2. ViGEmBus is used to create and use virtual gamepad devices. It can be downloaded and installed from https://github.com/ViGEm/ViGEmBus/releases/. Only 64-bit is supported.**(*)**

Once these programs are installed, download and extract the pianosouls source. Open a Powershell or Command Line window as administrator in the extracted folder and run:

> ```python .\setup.py install```

**Alternatively**, if you don't want to install pianosouls globally, it can be run directly from the extracted folder:

> ```python -m pianosouls```

Note that this requires you manually install it's dependency ```pygame```.

**(*)** Probably the only part of the program excluding 32-bit computers is ViGEmClient.dll, but as far as I know, this library **can** be built for x86. See section "ViGEm Client Native SDK/ViGEmClient.dll" for more information.

## Configuration
pianosouls uses human readable text files to configure sessions. These can be saved anywhere on your computer. From config/example.conf:
```
; example.conf
; An example configuration for pianosouls

; Anything written after a semicolon (;) is considered a comment. Comments
; can include human readable explanations or notes. They are ignored
; by pianosouls.

; Chord/note    Action
A4              Down    ; Playing the note A4 on a digital instrument results
                        ; in the virtual gamepad pressing down on the D-pad.
B4              Up      ; Similarly, playing B4 binds to D-pad up.
Bb4             Up      ; We can also specify many different notes to trigger
                        ; same actions.
F               Start   ; Any note F, played anywhere on the keyboard, presses
                        ; Start on the gamepad.
Cm7             Back    ; Playing the C minor 7th chord (anywhere on the
                        ; keyboard, in any inversion) presses Back.
D, F, A         LT      ; Playing the notes D, F and A at the same time
                        ; results in the left trigger being pressed. Listing 
                        ; these notes in particular would be identical to
                        ; writing "Dm".
GM7             LY-     ; Playing G dominant 7th results in the gamepad
                        ; pushing left stick (the L -part) down (the Y- -part).
AM7             LY+     ; Similarly, playing A dominant 7th results in
                        ; left stick up.

; MULTIPLE MIDI CHANNELS OR VIRTUAL GAMEPAD DEVICES
; You can declare any MIDI channel from 1 to 16. Everything listed after
; the line "Channel: 10" only applies to notes played on that channel.
; If no MIDI channel is specified, channel 1 is defaulted to. This means
; that everything we've listed so far is listened to on channel 1.
Channel: 10
; Similarly, you can declare additional virtual gamepad devices. Everything
; written after this next line triggers actions on a second gamepad,
; and running pianosouls creates 2 virtual gamepads instead of one.
Device: 2

; Let's put a couple in just for example's sake
; Chord/note    Action
Ebm             A       ; Playing E flat minor results in gamepad press A
Cbm             B       ; Playing C flat minor results in gamepad press B


; pianosouls expects the following keywords when reading configuration files:

; X360 gamepad inputs:
; Up, Down, Left, Right           D-pad
; A, B, X, Y, Start, Back, Guide  Face buttons
; LB, RB                          Left and right bumpers (L1 and R1)
; LT, RT                          Left and right triggers (L2 and R2)
; LS, RS                          Left and right stick press (L3 and R3)
; LX-, LX+                        Left stick left and right (left stick X-axis)
; LY+, LY-                        Left stick up and down (left stick Y-axis)
; RX-, RX+                        Right stick left and right (right stick X-axis)
; RY+, RY-                        Right stick up and down (right stick Y-axis)
 
; Chord names (root note C used as an example):
; Cm        C minor
; CM        C major
; Caug      C augmented
; Cdim      C diminished
; Cm7       C minor 7th
; Cmmaj7    C minor-major 7th
; Cmaj7     C major 7th
; CM7       C dominant 7th
; CM7b5     C dominant 7th flat 5
; Cm7b5     C minor 7th flat 5 (half-diminished)
; Cdim7     C diminished 7th
; Caug7     C augmented 7th
; Caugmaj7  C augmented major 7th
```
A real config file, then, might look something like this (config/example-darksouls.conf):
```
; Dark Souls

; Firelink Shrine theme
; Chord/note(s) Action
E, B            LY+
F#dim           LT
B, D#           RB
E1              Down
F#1             A
G1              Up
A1              Left
A1              RX-
B1              Right
B1              RX+
A0              Start
```
## Using pianosouls
pianosouls is started from the command line. If you installed the recommended way (and not the alternative), then open a Powershell or Command Line window in the folder where your config file resides (my_config.txt in this example), and run:
> ```pianosouls.exe -c my_config.txt```

The program first lists all MIDI input capable devices connected to your computer. From these, choose the one you plan on using to play.

And that's it! When the program is started, Windows detectes a new x360 controller "plugged in", and you can control it with the notes and chords you have previously configured in my_config.txt.

Oftentimes you'll want to change your configurations while the pianosouls program is already running, trying out which notes and chords work well for whatever you're playing. For this purpose, pianosouls can reload the config file by pressing R.

When you're done, Ctrl-C quits the program.

## Extending pianosouls
I tried to design pianosouls to be as modular as possible to accommodate use cases other than sending gamepad inputs. For these purposes, the output "API" module is actually loaded dynamically at startup, and can be specified with the ```--api``` argument when starting. ```vigemclient``` is defaulted to if no ```--api``` argument is given.

For example, a vJoy (http://vjoystick.sourceforge.net/site/index.php/77-vjoy/84-homepage-v200) feeder module ```vjoyfeeder``` is included with the source code and can be used to drive vJoy devices. Naturally, configurations must be (re-)written to send valid axis and button names; vJoy labels buttons 1-128, not ABXY.

This leaves pianosouls.py completely agnostic to *what* is actually done with the processed MIDI data, which enables the easy addition of custom output modules (say, keyboard and mouse emulation, just to give an example). See vjoyfeeder.py or vigemclient.py to learn what fucntions are expected to be available on output modules.

## ViGEm Client Native SDK/ViGEmClient.dll
pianosouls sources and consequently the installed python package includes the binary file "ViGEmClient.dll". This DLL is a completely non-modified redistribution of the ViGEm Client Native SDK, the source of which can be found at https://github.com/ViGEm/ViGEmClient. vigemclient.py uses this SDK to spawn and feed virtual x360 controllers in ViGEmBus.

ViGEm Client Native SDK is licensed under the MIT license and is copyright (c) 2018 Benjamin Höglinger-Stelzer.