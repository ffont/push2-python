import push2_python
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from threading import Thread
import threading
import mido
import base64
from PIL import Image
from io import BytesIO
import time
import numpy
import queue 
import logging
import mido

app = Flask(__name__)
sim_app = SocketIO(app)

app_thread_id = None

push_object = None
client_connected = False

midi_out = None


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
        return mido.Message('note_on' if not releasing else 'note_off', note=int(midi_trigger.replace('nn', '')), velocity=velocity, channel=0)
    elif midi_trigger.startswith('cc'):
        return mido.Message('control_change', control=int(midi_trigger.replace('cc', '')), value=value if not releasing else 0, channel=0)
    return None


class SimulatorController(object):

    next_frame = None
    black_frame = None
    last_time_frame_prepared = 0
    max_seconds_display_inactive = 2 
    color_palette = default_color_palette
    ws_message_queue = queue.Queue()

    def __init__(self):

        # Generate black frame to be used if display is not updated
        colors = ['{b:05b}{g:06b}{r:05b}'.format(r=0, g=0, b=0),
                  '{b:05b}{g:06b}{r:05b}'.format(r=0, g=0, b=0),
                  '{b:05b}{g:06b}{r:05b}'.format(r=0, g=0, b=0)]
        colors = [int(c, 2) for c in colors]
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
        self.black_frame = numpy.array(frame, dtype=numpy.uint16).transpose()


    def emit_ws_message(self, name, data):
        if threading.get_ident() != app_thread_id:
            # The flask-socketio default configuration for web sockets does not support emitting to the browser from different
            # threads. It looks like this should be possible using some external queue based on redis or the like, but to avoid
            # further complicating the setup and requirements, if for some reason we're trying to emit tot he browser from a 
            # different thread than the thread running the Flask server, we add the messages to a queue. That queue is being 
            # continuously pulled (every 100ms) from the browser (see index.html) and then messages are sent. This means that
            # the timing of the messages won't be accurate, but this seems like a reaosnable trade-off considering the nature
            # and purpose of the simulator.
            self.ws_message_queue.put((name, data))
        else:
            emit(name, data)

    def emit_messages_from_ws_queue(self):
        while not self.ws_message_queue.empty():
            name, data = self.ws_message_queue.get()
            emit(name, data)

        if time.time() - self.last_time_frame_prepared > self.max_seconds_display_inactive:
            self.prepare_and_display_in_simulator(self.black_frame, input_format=push2_python.constants.FRAME_FORMAT_BGR565, force=True)

    def clear_color_palette(self):
        self.color_palette = {}

    def update_color_palette_entry(self, color_index, color_rgb, color_bw):
        self.color_palette[color_index] = [color_rgb, color_bw]

    def set_element_color(self, midiTrigger, color_idx, animation_idx):
        rgb, bw_rgb = self.color_palette.get(color_idx, [(255, 255, 255), (255, 255, 255)])
        if rgb is None:
            rgb = (255, 255, 255)
        if bw_rgb is None:
            bw_rgb = (255, 255, 255)
        if client_connected:
            self.emit_ws_message('setElementColor', {'midiTrigger':midiTrigger, 'rgb': rgb, 'bwRgb': bw_rgb, 'blink': animation_idx != 0})            

    def prepare_and_display_in_simulator(self, frame, input_format=push2_python.constants.FRAME_FORMAT_BGR565, force=False):

        if time.time() - self.last_time_frame_prepared > 1.0/5.0 or force:  # Limit to 5 fps to save recources
            self.last_time_frame_prepared = time.time()
            
            # 'frame' should be an array as in display.display_frame method input
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
            self.emit_ws_message('setDisplay', {'base64Image': base64Image})
                

@sim_app.on('connect')
def test_connect():
    global client_connected
    client_connected = True
    push_object.trigger_action(push2_python.constants.ACTION_MIDI_CONNECTED)
    push_object.trigger_action(push2_python.constants.ACTION_DISPLAY_CONNECTED)
    logging.info('Simulator client connected')


@sim_app.on('disconnect')
def test_disconnect():
    global client_connected
    client_connected = False
    push_object.trigger_action(push2_python.constants.ACTION_MIDI_DISCONNECTED)
    push_object.trigger_action(push2_python.constants.ACTION_DISPLAY_DISCONNECTED)
    logging.info('Simulator client disconnected')


@sim_app.on('getPendingMessages')
def get_ws_messages_from_queue():
    push_object.simulator_controller.emit_messages_from_ws_queue()


@sim_app.on('padPressed')
def pad_pressed(midiTrigger):
    msg = make_midi_message_from_midi_trigger(midiTrigger)
    if midi_out is not None:
        midi_out.send(msg)
    push_object.pads.on_midi_message(msg)


@sim_app.on('padReleased')
def pad_released(midiTrigger):
    msg = make_midi_message_from_midi_trigger(midiTrigger, releasing=True)
    if midi_out is not None:
        midi_out.send(msg)
    push_object.pads.on_midi_message(msg)


@sim_app.on('buttonPressed')
def button_pressed(midiTrigger):
    msg = make_midi_message_from_midi_trigger(midiTrigger)
    if midi_out is not None:
        midi_out.send(msg)
    push_object.buttons.on_midi_message(msg)


@sim_app.on('buttonReleased')
def button_released(midiTrigger):
    msg = make_midi_message_from_midi_trigger(midiTrigger, releasing=True)
    if midi_out is not None:
        midi_out.send(msg)
    push_object.buttons.on_midi_message(msg)


@sim_app.on('encdoerTouched')
def encoder_pressed(midiTrigger):
    msg = make_midi_message_from_midi_trigger(midiTrigger, velocity=127)
    if midi_out is not None:
        midi_out.send(msg)
    push_object.encoders.on_midi_message(msg)


@sim_app.on('encdoerReleased')
def encoder_released(midiTrigger):
    msg = make_midi_message_from_midi_trigger(midiTrigger, velocity=0)
    if midi_out is not None:
        midi_out.send(msg)
    push_object.encoders.on_midi_message(msg)


@sim_app.on('encdoerRotated')
def encoder_rotated(midiTrigger, value):
    msg = make_midi_message_from_midi_trigger(midiTrigger, value=value)
    if midi_out is not None:
        midi_out.send(msg)
    push_object.encoders.on_midi_message(msg)


@app.route('/')
def index():
    return render_template('index.html')


def run_simulator_in_thread(port):
    global app_thread_id
    app_thread_id = threading.get_ident()
    logging.error('Running simulator at http://localhost:{}'.format(port))
    sim_app.run(app, port=port)


def start_simulator(_push_object, port, use_virtual_midi_out):
    global push_object, midi_out
    push_object = _push_object
    if use_virtual_midi_out:
        name = 'Push2Simulator'
        logging.info('Sending Push2 simulated messages to "{}" virtual midi output'.format(name))
        midi_out = mido.open_output(name, virtual=True)
    thread = Thread(target=run_simulator_in_thread, args=(port, ))
    thread.start()
    return SimulatorController()
