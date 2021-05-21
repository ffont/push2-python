import push2_python
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from threading import Thread
import mido
import base64
from PIL import Image
from io import BytesIO
import time
import numpy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uP3jUqqye3'
sim_app = SocketIO(app) # logger=True, engineio_logger=True

push_object = None
client_connected = False
latest_prepared_base64_image_to_send = None
latest_prepared_image_sent = False

default_color_palette = {
    0: [(0, 0, 0), (0 ,0 ,0)],
    3: [(265, 165, 0), None],
    8: [(255, 255, 0), None],
    15: [(0, 255, 255), None],
    16: [None, (128, 128, 128)],
    22: [(128, 0, 128), None],
    25: [(255, 0, 255), None],
    48: [None, (192, 192, 192)],
    122: [(255, 255, 255), None],
    123: [(192, 192, 192), None],
    124: [(128, 128, 128), None],
    125: [(0, 0, 255), None],
    126: [(0, 255, 0), None],
    127: [(255, 0, 0), (255, 255, 255)]
}

def make_midi_message_from_midi_trigger(midi_trigger, releasing=False, velocity=127, value=127):
    if midi_trigger.startswith('nn'):
        return mido.Message('note_on' if not releasing else 'note_off', note=int(midi_trigger.replace('nn', '')), velocity=velocity)
    if midi_trigger.startswith('cc'):
        return mido.Message('control_change', control=int(midi_trigger.replace('cc', '')), value=value if not releasing else 0)
    return None


class SimulatorController(object):

    next_frame = None
    color_palette = default_color_palette
    last_time_frame_prepared = 0

    def set_color_palette(self, new_color_palette):
        self.color_palette = new_color_palette

    def set_element_color(self, midiTrigger, color_idx, animation_idx):
        rgb, bw_rgb = self.color_palette.get(color_idx, [(255, 255, 255), (255, 255, 255)])
        if rgb is None:
            rgb = (255, 255, 255)
        if bw_rgb is None:
            bw_rgb = (255, 255, 255)
        if client_connected:
            try:
                emit('setElementColor', {'midiTrigger':midiTrigger, 'rgb': rgb, 'bwRgb': bw_rgb, 'blink': animation_idx != 0})
            except RuntimeError:
                pass

    def prepare_next_frame_for_display(self, frame, input_format=push2_python.constants.FRAME_FORMAT_BGR565):
        global latest_prepared_base64_image_to_send, latest_prepared_image_sent

        # 'frame' expects a "frame" as in display.display_frame method
        if time.time() - self.last_time_frame_prepared > 1.0/5.0:  # Limit fps to save recources
            self.last_time_frame_prepared = time.time()
            
            # We need to convert the frame to RGBA format first (so Pillow can read it later)
            if input_format == push2_python.constants.FRAME_FORMAT_RGB:
                frame = push2_python.display.rgb_to_bgr565(frame)

            frame = frame.transpose().flatten()
            rgb_frame = numpy.zeros(shape=(len(frame), 1), dtype=numpy.uint32).flatten()
            rgb_frame[:] = frame[:]
            
            if input_format == push2_python.constants.FRAME_FORMAT_RGB565:
                r_filter = int('1111100000000000', 2)
                g_filter = int('0000011111100000', 2)
                b_filter = int('0000000000011111', 2)
                frame_r_filtered = numpy.bitwise_and(rgb_frame, r_filter)
                frame_r_shifted = numpy.right_shift(frame_r_filtered, 8)  # Shift 8 to right so R sits in the the 0-7 right-most bits
                frame_g_filtered = numpy.bitwise_and(rgb_frame, g_filter)
                frame_g_shifted = numpy.left_shift(frame_g_filtered, 5)  # Shift 5 to the left so G sits at the 8-15 bits
                frame_b_filtered = numpy.bitwise_and(rgb_frame, b_filter)
                frame_b_shifted = numpy.left_shift(frame_b_filtered, 19)  # Shift 19 to the left so G sits at the 16-23 bits
                rgb_frame = frame_r_shifted + frame_g_shifted + frame_b_shifted  # Combine all channels
                rgb_frame = numpy.bitwise_or(rgb_frame, int('11111111000000000000000000000000', 2))  # Set alpha channel to "full!" (bits 24-32)

            elif input_format == push2_python.constants.FRAME_FORMAT_BGR565 or input_format == push2_python.constants.FRAME_FORMAT_RGB:
                r_filter = int('0000000000011111', 2)
                g_filter = int('0000011111100000', 2)
                b_filter = int('1111100000000000', 2)                
                frame_r_filtered = numpy.bitwise_and(rgb_frame, r_filter) 
                frame_r_shifted = numpy.left_shift(frame_r_filtered, 3)  # Shift 3 to left so R sits in the the 0-7 right-most bits
                frame_g_filtered = numpy.bitwise_and(rgb_frame, g_filter)
                frame_g_shifted = numpy.left_shift(frame_g_filtered, 5)  # Shift 5 to the left so G sits at the 8-15 bits
                frame_b_filtered = numpy.bitwise_and(rgb_frame, b_filter)
                frame_b_shifted = numpy.left_shift(frame_b_filtered, 8)  # Shift 8 to the left so G sits at the 16-23 bits
                rgb_frame = frame_r_shifted + frame_g_shifted + frame_b_shifted  # Combine all channels
                rgb_frame = numpy.bitwise_or(rgb_frame, int('11111111000000000000000000000000', 2))  # Set alpha channel to "full!" (bits 24-32)
     
            img = Image.frombytes('RGBA', (960, 160), rgb_frame.tobytes())
            buffered = BytesIO()
            img.save(buffered, format="png")
            base64Image = 'data:image/png;base64, ' + str(base64.b64encode(buffered.getvalue()))[2:-1]
            latest_prepared_base64_image_to_send = base64Image
            latest_prepared_image_sent = False
                

@sim_app.on('connect')
def test_connect():
    global client_connected
    client_connected = True
    print('Client connected')
    push_object.trigger_action(push2_python.constants.ACTION_MIDI_CONNECTED)
    push_object.trigger_action(push2_python.constants.ACTION_DISPLAY_CONNECTED)


@sim_app.on('disconnect')
def test_disconnect():
    global client_connected
    client_connected = False
    print('Client disconnected')
    push_object.trigger_action(push2_python.constants.ACTION_MIDI_DISCONNECTED)
    push_object.trigger_action(push2_python.constants.ACTION_DISPLAY_DISCONNECTED)


@sim_app.on('getNewDisplayImage')
def get_new_display_image():
    global latest_prepared_image_sent
    if not latest_prepared_image_sent:
        emit('setDisplay', {'base64Image': latest_prepared_base64_image_to_send})
        latest_prepared_image_sent = True
    

@sim_app.on('padPressed')
def pad_pressed(midiTrigger):
    msg = make_midi_message_from_midi_trigger(midiTrigger)
    push_object.pads.on_midi_message(msg)


@sim_app.on('padReleased')
def pad_released(midiTrigger):
    msg = make_midi_message_from_midi_trigger(midiTrigger, releasing=True)
    push_object.pads.on_midi_message(msg)


@sim_app.on('buttonPressed')
def button_pressed(midiTrigger):
    msg = make_midi_message_from_midi_trigger(midiTrigger)
    push_object.buttons.on_midi_message(msg)


@sim_app.on('buttonReleased')
def button_released(midiTrigger):
    msg = make_midi_message_from_midi_trigger(midiTrigger, releasing=True)
    push_object.buttons.on_midi_message(msg)


@sim_app.on('encdoerTouched')
def encoder_pressed(midiTrigger):
    msg = make_midi_message_from_midi_trigger(midiTrigger, velocity=127)
    push_object.encoders.on_midi_message(msg)


@sim_app.on('encdoerReleased')
def encoder_released(midiTrigger):
    msg = make_midi_message_from_midi_trigger(midiTrigger, velocity=0)
    push_object.encoders.on_midi_message(msg)


@sim_app.on('encdoerRotated')
def encoder_rotated(midiTrigger, value):
    msg = make_midi_message_from_midi_trigger(midiTrigger, value=value)
    push_object.encoders.on_midi_message(msg)


@app.route('/')
def index():
    return render_template('index.html')


def run_simulator_in_thread():
    sim_app.run(app, port=6128)


def start_simulator(_push_object):
    global push_object
    push_object = _push_object
    thread = Thread(target = run_simulator_in_thread)
    thread.start()
    return SimulatorController()
