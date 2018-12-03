# push2-python

Utils to interface with [Ableton's Push 2](https://www.ableton.com/en/push/) from Python.

These utils follow Ableton's [Push 2 MIDI and Display Interface Manual](https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc) to comunicating with Push 2. I recommend reading this before using this tools.

So far I only implemented some utils to **use the display** and some utils for **basic interaction with pads, buttons, encoders and the touchstrip**. More detailed interaction with each of these elements has not yet been implemented. Contributions are welcome :)

**NOTE**: I only testd the package in Python 3. Some things will not work on Python 2 but it should be easy to port.

## Install

You can install using `pip` and pointing at this repository:

```
pip install git+https://github.com/ffont/push2-python
```

This will install python requirements as well. Note however that `push2-python` requires [pyusb](https://github.com/pyusb/pyusb) which is based in [libusb](https://libusb.info/). You'll most probably need to manually install `libusb` for your operative system if `pip` does not do it for you.

## Documentation

Well, to be honest there is no proper documentation. However the use of this package is so simple that I hope it's going to be enough with the [code examples below](#code-examples) and the simple notes given here.

**TODO**: this section has not been written yet ;)


## Code examples

### Set up handlers for pads, encoders, etc...

```python
import push2_python

# Init Push2
push = push2_python.Push2()

# Now set up some action handlers that will trigger when interacting with Push2
# This is all done using decorators.
@push2_python.on_pad_pressed()
def on_pad_pressed(push, pad_n, pad_ij, velocity):
    print('Pad', pad_ij, 'pressed with velocity', velocity)

@push2_python.on_encoder_rotated()
def on_encoder_touched(push, encoder_name):
    print('Encoder', encoder_name, 'rotated')

@push2_python.on_touchstrip()
def on_touchstrip(push, value):
    print('Touchstrip touched with value', value)

# You can also set handlers for specic encoders or buttons by passing argument to the decorator
@push2_python.on_encoder_rotated(push2_python.constants.ENCODER_TRACK1_ENCODER)
def on_encoder_rotated(push, value):
    print('Encoder for Track 1 rotated with value', value)

@push2_python.on_button_pressed(push2_python.constants.BUTTON_1_16)
def on_button_pressed(push):
    print('Button 1/16 pressed')

# Now start infinite loop so the app keeps running
print('App runnnig...')
while True:
    pass
```

### Light up buttons and pads

```python
import push2_python

# Init Push2
push = push2_python.Push2()

# Start by setting all pad colors to white
push.pads.set_all_pads_to_color('white')

@push2_python.on_button_pressed()
def on_button_pressed(push, button_name):
    # Set pressed button color to white
    push.buttons.set_button_color(button_name, 'white')

@push2_python.on_button_released()
def on_button_released(push, button_name):
    # Set released button color to black (off)
    push.buttons.set_button_color(button_name, 'black')

@push2_python.on_pad_pressed()
def on_pad_pressed(push, pad_n, pad_ij, velocity):
    # Set pressed pad color to green
    push.pads.set_pad_color(pad_ij[0], pad_ij[1], 'green')

@push2_python.on_pad_released()
def on_pad_released(push, pad_n, pad_ij, velocity):
    # Set released pad color back to white
    push.pads.set_pad_color(pad_ij[0], pad_ij[1], 'white')

# Start infinite loop so the app keeps running
print('App runnnig...')
while True:
    pass
```

### Interface with the display

Here you have some example code for interfacing with Push2's display. Note this code example requires `pillow` Python package, install it with `pip install pillow`.

```python
import push2_python
import random
import numpy
from PIL import Image

# Init Push2
push = push2_python.Push2()

# Define util function to generate a frame with some colors to be shown in the display
# Frames are created as matrices of shape 960x160 and with colors defined in bgr565 format
# This function is defined in a rather silly way, could probably be optimized a lot ;)
def generate_3_color_frame():
    colors = ['{b:05b}{g:06b}{r:05b}'.format(
                  r=int(32*random.random()), g=int(64*random.random()), b=int(32*random.random())),
              '{b:05b}{g:06b}{r:05b}'.format(
                  r=int(32*random.random()), g=int(64*random.random()), b=int(32*random.random())),
              '{b:05b}{g:06b}{r:05b}'.format(
                  r=int(32*random.random()), g=int(64*random.random()), b=int(32*random.random()))]
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
    return numpy.array(frame, dtype=numpy.uint16).transpose()

# Pre-generate three different color frames
color_frames = [generate_3_color_frame(), generate_3_color_frame(), generate_3_color_frame()]

# Now crate an extra frame which loads an image from a file. Image must be 960x160 pixels.
img = Image.open('test_img_960x160.png')
img_array = numpy.array(img)
frame = img_array/255  # Convert rgb values to [0.0, 1.0] floats

# Because the pixel format returned by Image.open is not the one required for Push2's display, this frame needs to be prepared before sending it to Push. This conversion takes a bit of time so we do it offline. Some formats can be converted on the fly by `push2-python` but not the RGB format retruned by PIL.
prepared_img_frame = push.display.prepare_frame(frame, input_format=push2_python.constants.FRAME_FORMAT_RGB)

# Now lets configure some action handlers which will display frames in Push2's display in reaction to pad and button presses
@push2_python.on_pad_pressed()
def on_pad_pressed(push, pad_n, pad_ij, velocity):
    # Display one of the three color frames on the display
    random_frame = random.choice(color_frames)
    push2.display.display_frame(random_frame)

@push2_python.on_button_pressed()
def on_button_pressed(push, button_name):
    # Display the frame with the loaded image
    push2.display.display_prepared_frame(prepared_img_frame)

# Start infinite loop so the app keeps running
print('App runnnig...')
while True:
    pass
```
