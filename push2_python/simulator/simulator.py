import push2_python
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from threading import Thread
import mido
import base64
from PIL import Image
from io import BytesIO
import time
import random

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

def make_midi_message_from_midi_trigger(midi_trigger, releasing=False):
    if midi_trigger.startswith('nn'):
        return mido.Message('note_on' if not releasing else 'note_off', note=int(midi_trigger.replace('nn', '')), velocity=127)
    if midi_trigger.startswith('cc'):
        return mido.Message('control_change', control=int(midi_trigger.replace('cc', '')), value=127 if not releasing else 0)
    return None


class SimulatorController(object):

    next_frame = None
    color_palette = default_color_palette
    last_time_frame_prepared = 0

    def set_color_palette(self, new_color_palette):
        self.color_palette = new_color_palette

    def set_element_color(self, midiTrigger, color_idx):
        rgb, bw_rgb = self.color_palette.get(color_idx, [(255, 255, 255), (255, 255, 255)])
        if rgb is None:
            rgb = (255, 255, 255)
        if bw_rgb is None:
            bw_rgb = (255, 255, 255)
        if client_connected:
            try:
                emit('setElementColor', {'midiTrigger':midiTrigger, 'rgb': rgb, 'bwRgb': bw_rgb})
            except RuntimeError:
                pass

    def prepare_next_frame_for_display(self, frame):
        global latest_prepared_base64_image_to_send, latest_prepared_image_sent
        
        # 'frame' expects same format as in push.display.display_frame
        if time.time() - self.last_time_frame_prepared > 1.0/5.0:  # Limit fps to save recources
            self.last_time_frame_prepared = time.time()
            img = Image.fromarray(frame.transpose(), 'I;16')
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


@sim_app.on('disconnect')
def test_disconnect():
    global client_connected
    client_connected = False
    print('Client disconnected')


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


@app.route('/')
def index():
    return render_template('index.html')


def run_simulator_in_thread():
    sim_app.run(app)


def start_simulator(_push_object):
    global push_object
    push_object = _push_object
    thread = Thread(target = run_simulator_in_thread)
    thread.start()
    return SimulatorController()
