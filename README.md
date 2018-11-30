# push2-python
Utils to interface with [Ableton's Push 2](https://www.ableton.com/en/push/) from Python.

These utils follow Ableton's [Push 2 MIDI and Display Interface Manual](https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc) to facilitate comunicating with Push 2.

So far I only implemented some **utils to use the display** and some **basic utils to interface with pads, buttons, encoders and the touchstrip**. More detailed interaction with each of these elements has not yet been implemented. I plan to include utils for this as well, but contributions are also welcome :)

**NOTE 1**: I only testd the utils in Python 3, but it should work with 2 as well.

**NOTE 2**: this package requires [pyusb](https://github.com/pyusb/pyusb) which is based in [libusb](https://libusb.info/). You'll need to manually install `libusb` for your operative system if `pip` does not do it for you.


## Interfacing with Push2's display

Here's some example code, easy isn't it?

```python
import push2_python
import random
import time


# Init Push2
push = push2_python.Push2()


# Set up some action handlers that will trigger when interacting with Push2
@push2_python.on_pad_pressed()
def on_pad_pressed(push, pad_n, pad_ij, velocity):
    print('Pad', pad_ij, 'pressed with velocity', velocity)


@push2_python.on_touchstrip()
def on_touchstrip(push, value):
    print('Touchstrip touched with value', value)


@push2_python.on_encoder_rotated(push2_python.constants.ENCODER_TRACK1_ENCODER)
def on_encoder_rotated(push, value):
    print('Encoder for Track 1 rotated with value', value)


@push2_python.on_encoder_touched()
def on_encoder_touched(push, encoder_name):
    print('Encoder', encoder_name, 'touched')


@push2_python.on_button_pressed(push2_python.constants.BUTTON_1_16)
def on_button_pressed(push):
    print('Button 1/16 pressed')


# Set pad and button colors
for color in ['white', 'red', 'green', 'blue']:
    push.pads.set_all_pads_to_color(color)
    push.buttons.set_button_color(push2_python.constants.BUTTON_PLAY, color)
    time.sleep(0.5)


# Show some colors on the display
def generate_3_color_frame():
    # Util function to generate an image with some colors
    colors = ['{b:05b}{g:06b}{r:05b}'.format(r=random.random(), g=random.random(), b=random.random()),
              '{b:05b}{g:06b}{r:05b}'.format(
                  r=random.random(), g=random.random(), b=random.random()),
              '{b:05b}{g:06b}{r:05b}'.format(r=random.random(), g=random.random(), b=random.random())]
    line_bytes = []
    for i in range(0, 960):  # 960 pixels per line
        if i <= 960 // 3:
            line_bytes.append(colors[0])
        elif 960 // 3 < i <= 2 * 960 // 3:
            line_bytes.append(colors[1])
        else:
            line_bytes.append(colors[2])
    frame = []
    for i in range(0, 160):  # 160 lines
        frame.append(line_bytes)
    return frame

for j in range(0, 5):
    frame = generate_3_color_frame()
    push.display.display_frame(frame)
    time.sleep(1)

# Repeat display last frame so the image stays on screen
for j in range(0, 5):
    push.display.display_last_frame()
    time.sleep(1)

# Start infinite loop. From now on app only reacts to action handlers
print('App runnnig...')
while True:
    pass

```
