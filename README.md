# push2-python
Utils to interface with [Ableton's Push 2](https://www.ableton.com/en/push/) from Python.

These utils follow Ableton's [Push 2 MIDI and Display Interface Manual](https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc) to facilitate comunicating with Push 2.

So far I only implemented some **utils to communicate with the display**. Interfacing with buttons, pads and encoders is all done via MIDI and therefore is relatively straightforward. I plan to include utils for this as well, but contributions are also welcome :)

**NOTE 1**: I only testd the utils in Python 3, but it should work with 2 as well.
**NOTE 2**: this package requires [pyusb](https://github.com/pyusb/pyusb) which is based in [libusb](https://libusb.info/). You'll need to manually install `libusb` for your operative system if `pip` does not do it for you.


## Interfacing with Push2's display

Here's some example code, easy isn't it?

```python
from push2_python import Push2
import random
import time


def generate_3_color_frame():
    colors = [(random.random(), random.random(), random.random()),
              (random.random(), random.random(), random.random()),
              (random.random(), random.random(), random.random())]
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


def generate_frame_from_img(img_path):
    from PIL import Image
    import numpy
    img = Image.open(img_path)
    img_array = numpy.array(img)
    frame = img_array/255
    return frame


# Init Push2
push = Push2()

# Generate consecutive color frames
for j in range(0, 5):
    frame = generate_3_color_frame()
    push.display_frame(frame)
    time.sleep(1)

# Generate frame from loaded image (requires "pip install Pillow numpy")
frame = generate_frame_from_img("test_img_960x160.png")
push.display_frame(frame)

# Repeat display last frame so the image stays on screen
for j in range(0, 5):
    push.display_last_frame()
    time.sleep(1)
```
