import push2_python
import mido
import time
import random

midi_outport = mido.open_output('Push2App', virtual=True)


def pad_ij_to_midi_note(pad_ij):
        root_midi_note = 32  # Pad bottom-left note
        return root_midi_note + ((7 - pad_ij[0]) * 5 + pad_ij[1])

@push2_python.action_handler(push2_python.constants.ACTION_PAD_PRESSED)
def on_pad_pressed(push, pad_n, pad_ij, velocity):
    push.pads.set_pad_color(pad_ij[0], pad_ij[1], 'green')
    msg = mido.Message(
        'note_on', note=pad_ij_to_midi_note(pad_ij), velocity=velocity)
    midi_outport.send(msg)


@push2_python.action_handler(push2_python.constants.ACTION_PAD_RELEASED)
def on_pad_released(push, pad_n, pad_ij, velocity):
    push.pads.set_pad_color(pad_ij[0], pad_ij[1], 'white')
    msg = mido.Message(
        'note_off', note=pad_ij_to_midi_note(pad_ij), velocity=velocity)
    midi_outport.send(msg)


@push2_python.action_handler(push2_python.constants.ACTION_PAD_AFTERTOUCH)
def on_pad_aftertouch(push, pad_n, pad_ij, velocity):
    msg = mido.Message(
        'polytouch', note=pad_ij_to_midi_note(pad_ij), value=velocity)
    midi_outport.send(msg)


@push2_python.action_handler(push2_python.constants.ACTION_TOUCHSTRIP_TOUCHED)
def on_touchstrip_touched(push, value):
    msg = mido.Message('pitchwheel', pitch=value)
    midi_outport.send(msg)
    

@push2_python.action_handler(push2_python.constants.ACTION_BUTTON_PRESSED)
def on_button_pressed(push, button_name):
    print('Button', button_name, 'pressed')


@push2_python.action_handler(push2_python.constants.ACTION_BUTTON_RELEASED)
def on_button_released(push, button_name):
    print('Button', button_name, 'released')


push = push2_python.Push2()
push.pads.set_polyphonic_aftertouch()
push.pads.set_all_pads_to_color('white')


print('App runnnig...')
while True:
    pass
