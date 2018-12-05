# push2-python

Utils to interface with [Ableton's Push 2](https://www.ableton.com/en/push/) from Python.

These utils follow Ableton's [Push 2 MIDI and Display Interface Manual](https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc) for comunicating with Push 2. I recommend reading Ableton's manual before using this tools.

So far I only implemented some utils to **interface with the display** and some utils for **basic interaction with pads, buttons, encoders and the touchstrip**. More detailed interaction with each of these elements (e.g. changing color palettes, support for led blinking, advanced touchstrip configuration, etc.) has not been implemented. Contributions are welcome :)

I only testd the package in **Python 3** and **macOS**. Some things will not work on Python 2 but it should be easy to port. Not how it will work on Windows/Linux. It is possible that MIDI port names (see [constants.py](https://github.com/ffont/push2-python/blob/master/push2_python/constants.py#L12-L13)) need to be changed to correctly reach Push2 in Windows/Linux.


## Table of Contents

* [Install](#install)
* [Documentation](#documentation)
* [Code examples](#code-examples)
    * [Set up handlers for pads, encoders, buttons and the touchstrip...](#set-up-handlers-for-pads-encoders-buttons-and-the-touchstrip)
    * [Light up buttons and pads](#light-up-buttons-and-pads)
    * [Interface with the display (static content)](#interface-with-the-display-static-content)
    * [Interface with the display (dynamic content)](#interface-with-the-display-dynamic-content)


## Install

You can install using `pip` and pointing at this repository:

```
pip install git+https://github.com/ffont/push2-python
```

This will install python requirements as well. Note however that `push2-python` requires [pyusb](https://github.com/pyusb/pyusb) which is based in [libusb](https://libusb.info/). You'll most probably need to manually install `libusb` for your operative system if `pip` does not do it for you.

## Documentation

Well, to be honest there is no proper documentation. However the use of this package is so simple that I hope it's going to be enough with the [code examples below](#code-examples) and the simple notes given here.

 **Initializing Push** 
 
 To interface with Push2 you'll first need to import `push2_python` and initialize a Python object as follows:

```python
import push2_python
push = push2_python.Push2() 
```

You can pass the optional argument `use_user_midi_port` when initializing `push` to tell it to use User MIDI port instead of Live MIDI port. Check [MIDI interface access](https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#midi-interface-access) and [MIDI mode](https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#MIDI%20Mode) sections of the [Push 2 MIDI and Display Interface Manual](https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc) for more information.

**Setting action handlers for buttons, encoders, pads and the touchstrip**

You can easily set action handlers that will trigger functions when the physical pads, buttons, encoders or the touchtrip are used. You do that by adding **Python decorators** to the functions that will be triggered in each case. The available decorators and the arguments that must be present in the decorated functions are [described here](https://github.com/ffont/push2-python/blob/master/push2_python/__init__.py#L128).

**Set pad and button colors**

TODO (for now see code examples below which should be useful enough to get you started)

**Interface with the display**

TODO (for now see code examples below which should be useful enough to get you started)


## Code examples

### Set up handlers for pads, encoders, buttons and the touchstrip...

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
def on_encoder_rotated(push, encoder_name, increment):
    print('Encoder', encoder_name, 'rotated', increment)

@push2_python.on_touchstrip()
def on_touchstrip(push, value):
    print('Touchstrip touched with value', value)

# You can also set handlers for specic encoders or buttons by passing argument to the decorator
@push2_python.on_encoder_rotated(push2_python.constants.ENCODER_TRACK1_ENCODER)
def on_encoder1_rotated(push, incrememnt):
    print('Encoder for Track 1 rotated with increment', increment)

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

### Interface with the display (static content)

Here you have some example code for interfacing with Push2's display. Note that this code example requires [`pillow`](https://python-pillow.org/) Python package, install it with `pip install pillow`.

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

# Pre-generate different color frames
color_frames = list()
for i in range(0, 20):
    color_frames.append(generate_3_color_frame())

# Now crate an extra frame which loads an image from a file. Image must be 960x160 pixels.
img = Image.open('test_img_960x160.png')
img_array = numpy.array(img)
frame = img_array/255  # Convert rgb values to [0.0, 1.0] floats

# Because the pixel format returned by Image.open is not the one required for Push2's display,
# this frame needs to be prepared before sending it to Push. This conversion takes a bit of 
# time so we do it offline. Some formats can be converted on the fly by `push2-python` but not 
# the RGB format retruned by PIL.
prepared_img_frame = \
    push.display.prepare_frame(frame, input_format=push2_python.constants.FRAME_FORMAT_RGB)

# Now lets configure some action handlers which will display frames in Push2's display in 
# reaction to pad and button presses
@push2_python.on_pad_pressed()
def on_pad_pressed(push, pad_n, pad_ij, velocity):
    # Display one of the three color frames on the display
    random_frame = random.choice(color_frames)
    push.display.display_frame(random_frame)

@push2_python.on_button_pressed()
def on_button_pressed(push, button_name):
    # Display the frame with the loaded image
    push.display.display_prepared_frame(prepared_img_frame)

# Start infinite loop so the app keeps running
print('App runnnig...')
while True:
    pass
```

### Interface with the display (dynamic content)

And here is a more advanced example of interfacing with the display. In this case display frames are generated dynamically and show some values that can be modified by rotating the encoders. Note that this code example requires [`pycairo`](https://github.com/pygobject/pycairo) Python package, install it with `pip install pycairo` (you'll most probably also need to install [`cairo`](https://www.cairographics.org/) before that, see [this page](https://pycairo.readthedocs.io/en/latest/getting_started.html) for info on that).

```python
import push2_python
import cairo
import numpy
import random
import time

# Init Push2
push = push2_python.Push2()

# Init dictionary to store the state of encoders
encoders_state = dict()
max_encoder_value = 100
for encoder_name in push.encoders.available_names:
    encoders_state[encoder_name] = {
        'value': int(random.random() * max_encoder_value),
        'color': [random.random(), random.random(), random.random()],
    }
last_selected_encoder = list(encoders_state.keys())[0]

# Function that generates the contents of the frame do be displayed
def generate_display_frame(encoder_value, encoder_color, encoder_name):

    # Prepare cairo canvas
    WIDTH, HEIGHT = push2_python.constants.DISPLAY_LINE_PIXELS, push2_python.constants.DISPLAY_N_LINES
    surface = cairo.ImageSurface(cairo.FORMAT_RGB16_565, WIDTH, HEIGHT)
    ctx = cairo.Context(surface)

    # Draw rectangle with width proportional to encoders' value
    ctx.set_source_rgb(*encoder_color)
    ctx.rectangle(0, 0, WIDTH * (encoder_value/max_encoder_value), HEIGHT)
    ctx.fill()

    # Add text with encoder name and value
    ctx.set_source_rgb(1, 1, 1)
    font_size = HEIGHT//3
    ctx.set_font_size(font_size)
    ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.move_to(10, font_size * 2)
    ctx.show_text("{0}: {1}".format(encoder_name, encoder_value))

    # Turn canvas into numpy array compatible with push.display.display_frame method
    buf = surface.get_data()
    frame = numpy.ndarray(shape=(HEIGHT, WIDTH), dtype=numpy.uint16, buffer=buf)
    frame = frame.transpose()
    return frame

# Set up action handlers to react to encoder touches and rotation
@push2_python.on_encoder_rotated()
def on_encoder_rotated(push, encoder_name, increment):
    def update_encoder_value(encoder_idx, increment):
        updated_value = int(encoders_state[encoder_idx]['value'] + increment)
        if updated_value < 0:
            encoders_state[encoder_idx]['value'] = 0
        elif updated_value > max_encoder_value:
            encoders_state[encoder_idx]['value'] = max_encoder_value
        else:
            encoders_state[encoder_idx]['value'] = updated_value

    update_encoder_value(encoder_name, increment)
    global last_selected_encoder
    last_selected_encoder = encoder_name

@push2_python.on_encoder_touched()
def on_encoder_touched(push, encoder_name):
    global last_selected_encoder
    last_selected_encoder = encoder_name

# Draw method that will generate the frame to be shown on the display
def draw():
    encoder_value = encoders_state[last_selected_encoder]['value']
    encoder_color = encoders_state[last_selected_encoder]['color']
    frame = generate_display_frame(encoder_value, encoder_color, last_selected_encoder)
    push.display.display_frame(frame, input_format=push2_python.constants.FRAME_FORMAT_RGB565)

# Now start infinite loop so the app keeps running
print('App runnnig...')
while True:
    draw()
    time.sleep(1.0/30)  # Sart drawing loop, aim at ~30fps
```
