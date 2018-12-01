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


# Start infinite loop. From now on app only reacts to action handlers
print('App runnnig...')
while True:
    pass
```

Now let's try setting pad and button colors when these are pressed:

```python
import push2_python

# Init Push2
push = push2_python.Push2()

# Start by setting all pad colors to white
push.pads.set_all_pads_to_color('white')

@push2_python.on_button_pressed()
def on_button_pressed(push, button_name):
    push.buttons.set_button_color(button_name, 'white')

@push2_python.on_button_released()
def on_button_released(push, button_name):
    push.buttons.set_button_color(button_name, 'black')

@push2_python.on_pad_pressed()
def on_pad_pressed(push, pad_n, pad_ij, velocity):
    push.pads.set_pad_color(pad_ij[0], pad_ij[1], 'green')

@push2_python.on_pad_released()
def on_pad_released(push, pad_n, pad_ij, velocity):
    push.pads.set_pad_color(pad_ij[0], pad_ij[1], 'white')

# Start infinite loop. From now on app only reacts to action handlers
print('App runnnig...')
while True:
    pass
```


Finally let's see how to interface with the display:

```python
import push2_python
import random
from PIL import Image
import numpy


# Init Push2
push = push2_python.Push2()

# Define util function to generate a frame with some colors to be shown in the display
# Frames are created as a matrix of shape 960x160 and with colors defined in bgr565 format
def generate_3_color_frame():
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

color_frames = [generate_3_color_frame(), generate_3_color_frame(), generate_3_color_frame()]

# Crate an extra frame by loading an image from a file
img = Image.open('test_img_960x160.png')
img_array = numpy.array(img)
frame = img_array/255  # Convert rgb values to [0.0, 1.0] floats
# Frame needs to be prepared before displaying as the format needs to be converted to one suitable for Push2's display
# Some formats can be converted on the fly but not the RGB format retruned by PIL
prepared_img_frame = push.display.prepare_frame(frame, input_format=push2_python.constants.FRAME_FORMAT_RGB)

@push2_python.on_pad_pressed()
def on_pad_pressed(push, pad_n, pad_ij, velocity):
    # Display one of the three color frames on the display
    random_frame = random.choice(color_frames)
    push2.display.display_frame(random_frame)

@push2_python.on_button_pressed()
def on_button_pressed(push, button_name):
    # Display the frame with the loaded image
    push2.display.display_prepared_frame(prepared_img_frame)

# Start infinite loop. From now on app only reacts to action handlers
print('App runnnig...')
while True:
    pass

```
