from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from threading import Thread

app = Flask(__name__)
app.config['SECRET_KEY'] = 'uP3jUqqye3'
sim_app = SocketIO(app) # logger=True, engineio_logger=True
push_object = None

@sim_app.on('connect')
def test_connect():
    print('Client connected')
    emit('my response', {'data': 'Connected'})

@sim_app.on('disconnect')
def test_disconnect():
    print('Client disconnected')

@sim_app.on('my_event')
def handle_my_custom_event(arg1, arg2, arg3):
    print(push_object)
    print('received args: ' + str(arg1) + str(arg2) + str(arg3))
    emit('my response', (arg1, arg2, arg3))

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
