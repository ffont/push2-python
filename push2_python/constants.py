import os
import platform

# Push2 map file
PUSH2_MAP_FILE_PATH = os.path.join(os.path.dirname(__file__), 'Push2-map.json')

# USB device/transfer settings
ABLETON_VENDOR_ID = 0x2982
PUSH2_PRODUCT_ID = 0x1967
USB_TRANSFER_TIMEOUT = 1000

# MIDI PORT NAMES

def is_push_midi_in_port_name(port_name, use_user_port=False):
    """Returns True if the given 'port_name' is the MIDI port name corresponding to Push2 MIDI
    input for the current OS platform. If 'use_user_port', it will check against Push2 User port instead
    of Push2 Live port.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#21-midi-interface-access
    """
    if platform.system() == "Linux":
        if not use_user_port:
            return 'Ableton Push' in port_name and port_name.endswith(':0')  # 'Ableton Push 2 nn:0', with nn being a variable number
        else:
            return 'Ableton Push' in port_name and port_name.endswith(':1')  # 'Ableton Push 2 nn:1', with nn being a variable number
    elif platform.system() == "Windows":
        if not use_user_port: # this uses the Ableton Live Midi Port
            return 'Ableton Push 2' in port_name  # 'Ableton Push 2 nn', with nn being a variable number
        else:  # user port
            return 'MIDIIN2 (Ableton Push 2)' in port_name  # 'MIDIIN2 (Ableton Push 2) nn', with nn being a variable number
    else: #macOS
        if not use_user_port:
            return 'Ableton Push 2 Live Port' in port_name
        else:
            return 'Ableton Push 2 User Port' in port_name


def is_push_midi_out_port_name(port_name, use_user_port=False):
    """Returns True if the given 'port_name' is the MIDI port name corresponding to Push2 MIDI
    output for the current OS platform. If 'use_user_port', it will check against Push2 User port instead
    of Push2 Live port.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#21-midi-interface-access
    """
    if platform.system() == "Linux":
        if not use_user_port:
            return 'Ableton Push' in port_name and port_name.endswith(':0')  # 'Ableton Push 2 nn:0', with nn being a variable number
        else:
            return 'Ableton Push' in port_name and port_name.endswith(':1')  # 'Ableton Push 2 nn:1', with nn being a variable number
    elif platform.system() == "Windows":
        if not use_user_port:  # ableton live midi port
            return 'Ableton Push 2' in port_name  # 'Ableton Push 2 nn', with nn being a variable number
        else:  # user port
            return 'MIDIOUT2 (Ableton Push 2)' in port_name  # 'MIDIIN2 (Ableton Push 2) nn', with nn being a variable number
    else: #macOS
        if not use_user_port:
            return 'Ableton Push 2 Live Port' == port_name
        else:
            return 'Ableton Push 2 User Port' == port_name


PUSH2_RECONNECT_INTERVAL = 0.05  # 50 ms
PUSH2_MIDI_ACTIVE_SENSING_MAX_INTERVAL = 0.5  # 0.5 seconds

MIDO_NOTEON = 'note_on'
MIDO_NOTEOFF = 'note_off'
MIDO_POLYAT = 'polytouch'
MIDO_AFTERTOUCH = 'aftertouch'
MIDO_PITCWHEEL = 'pitchwheel'
MIDO_CONTROLCHANGE = 'control_change'

PUSH2_SYSEX_PREFACE_BYTES = [0xF0, 0x00, 0x21, 0x1D, 0x01, 0x01]
PUSH2_SYSEX_END_BYTES = [0xF7]

# Push 2 Display
DISPLAY_FRAME_HEADER = [0xff, 0xcc, 0xaa, 0x88,
                        0x00, 0x00, 0x00, 0x00,
                        0x00, 0x00, 0x00, 0x00,
                        0x00, 0x00, 0x00, 0x00]
DISPLAY_N_LINES = 160
DISPLAY_LINE_PIXELS = 960
DISPLAY_PIXEL_BYTES = 2  # bytes
DISPLAY_LINE_FILLER_BYTES = 128
DISPLAY_LINE_SIZE = DISPLAY_LINE_PIXELS * \
    DISPLAY_PIXEL_BYTES + DISPLAY_LINE_FILLER_BYTES
DISPLAY_N_LINES_PER_BUFFER = 8
DISPLAY_BUFFER_SIZE = DISPLAY_LINE_SIZE * DISPLAY_N_LINES_PER_BUFFER
DISPLAY_FRAME_XOR_PATTERN = [0xE7F3, 0xE7FF] * (
    ((DISPLAY_LINE_PIXELS + (DISPLAY_LINE_FILLER_BYTES // 2)) * DISPLAY_N_LINES) // 2)
FRAME_FORMAT_BGR565 = 'bgr565'
FRAME_FORMAT_RGB565 = 'rgb565'
FRAME_FORMAT_RGB = 'rgb'

# LED rgb default color palette
# Color palette is defined as a dictionary where keys are a color index [0..127] and
# values are a 2-element list with the first element corresponding to the given RGB color name
# for that index and the second element being the given BW color name for that index
# This palette can be cusomized using `Push2.set_color_palette_entry` method.
DEFAULT_COLOR_PALETTE = {
    0: ['black', 'black'],
    3: ['orange', None],
    8: ['yellow', None],
    15: ['turquoise', None],
    16: [None, 'dark_gray'],
    22: ['purple', None],
    25: ['pink', None],
    48: [None, 'light_gray'],
    122: ['white', None],
    123: ['light_gray', None],
    124: ['dark_gray', None],
    125: ['blue', None],
    126: ['green', None],
    127: ['red', 'white']
}
DEFAULT_RGB_COLOR = 126
DEFAULT_BW_COLOR = 127

# Led animations
# Because push2-python does not send MIDI clock messages to push, all animations will run synced to a 120bpm tempo
# See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#268-led-animation
# for more info on what animation names mean
ANIMATION_STATIC = 0
ANIMATION_ONESHOT_24TH = 1
ANIMATION_ONESHOT_16TH = 2
ANIMATION_ONESHOT_8TH = 3
ANIMATION_ONESHOT_QUARTER = 4
ANIMATION_ONESHOT_HALF = 5
ANIMATION_PULSING_24TH = 6
ANIMATION_PULSING_16TH = 7
ANIMATION_PULSING_8TH = 8
ANIMATION_PULSING_QUARTER = 9
ANIMATION_PULSING_HALF = 10
ANIMATION_BLINKING_24TH = 11
ANIMATION_BLINKING_16TH = 12
ANIMATION_BLINKING_8TH = 13
ANIMATION_BLINKING_QUARTER = 14
ANIMATION_BLINKING_HALF = 15
ANIMATION_DEFAULT = ANIMATION_STATIC

# Push2 actions
ACTION_PAD_PRESSED = 'on_pad_pressed'
ACTION_PAD_RELEASED = 'on_pad_released'
ACTION_PAD_AFTERTOUCH = 'on_pad_aftertouch'
ACTION_TOUCHSTRIP_TOUCHED = 'on_touchstrip_touched'
ACTION_BUTTON_PRESSED = 'on_button_pressed'
ACTION_BUTTON_RELEASED = 'on_button_released'
ACTION_ENCODER_ROTATED = 'on_encoder_rotated'
ACTION_ENCODER_TOUCHED = 'on_encoder_touched'
ACTION_ENCODER_RELEASED = 'on_encoder_released'
ACTION_DISPLAY_CONNECTED = 'on_display_connected'
ACTION_DISPLAY_DISCONNECTED = 'on_display_disconnected'
ACTION_MIDI_CONNECTED = 'on_midi_connected'
ACTION_MIDI_DISCONNECTED = 'on_midi_disconnected'
ACTION_SUSTAIN_PEDAL = 'on_sustain_pedal'

# Push2 button names
# NOTE: the list of button names is here to facilitate autocompletion when developing apps using push2_python package, but is not needed for the package
# This list was generated using the following code:
# import json
# data = json.load(open('push2_python/Push2-map.json'))
# for item in data['Parts']['Buttons']:
#     print('BUTTON_{0} = \'{1}\''.format(item['Name'].replace(' ', '_').replace('/', '_').upper(), item['Name']))
BUTTON_TAP_TEMPO = 'Tap Tempo'
BUTTON_METRONOME = 'Metronome'
BUTTON_DELETE = 'Delete'
BUTTON_UNDO = 'Undo'
BUTTON_MUTE = 'Mute'
BUTTON_SOLO = 'Solo'
BUTTON_STOP = 'Stop'
BUTTON_CONVERT = 'Convert'
BUTTON_DOUBLE_LOOP = 'Double Loop'
BUTTON_QUANTIZE = 'Quantize'
BUTTON_DUPLICATE = 'Duplicate'
BUTTON_NEW = 'New'
BUTTON_FIXED_LENGTH = 'Fixed Length'
BUTTON_AUTOMATE = 'Automate'
BUTTON_RECORD = 'Record'
BUTTON_PLAY = 'Play'
BUTTON_UPPER_ROW_1 = 'Upper Row 1'
BUTTON_UPPER_ROW_2 = 'Upper Row 2'
BUTTON_UPPER_ROW_3 = 'Upper Row 3'
BUTTON_UPPER_ROW_4 = 'Upper Row 4'
BUTTON_UPPER_ROW_5 = 'Upper Row 5'
BUTTON_UPPER_ROW_6 = 'Upper Row 6'
BUTTON_UPPER_ROW_7 = 'Upper Row 7'
BUTTON_UPPER_ROW_8 = 'Upper Row 8'
BUTTON_LOWER_ROW_1 = 'Lower Row 1'
BUTTON_LOWER_ROW_2 = 'Lower Row 2'
BUTTON_LOWER_ROW_3 = 'Lower Row 3'
BUTTON_LOWER_ROW_4 = 'Lower Row 4'
BUTTON_LOWER_ROW_5 = 'Lower Row 5'
BUTTON_LOWER_ROW_6 = 'Lower Row 6'
BUTTON_LOWER_ROW_7 = 'Lower Row 7'
BUTTON_LOWER_ROW_8 = 'Lower Row 8'
BUTTON_1_32T = '1/32t'
BUTTON_1_32 = '1/32'
BUTTON_1_16T = '1/16t'
BUTTON_1_16 = '1/16'
BUTTON_1_8T = '1/8t'
BUTTON_1_8 = '1/8'
BUTTON_1_4T = '1/4t'
BUTTON_1_4 = '1/4'
BUTTON_SETUP = 'Setup'
BUTTON_USER = 'User'
BUTTON_ADD_DEVICE = 'Add Device'
BUTTON_ADD_TRACK = 'Add Track'
BUTTON_DEVICE = 'Device'
BUTTON_MIX = 'Mix'
BUTTON_BROWSE = 'Browse'
BUTTON_CLIP = 'Clip'
BUTTON_MASTER = 'Master'
BUTTON_UP = 'Up'
BUTTON_DOWN = 'Down'
BUTTON_LEFT = 'Left'
BUTTON_RIGHT = 'Right'
BUTTON_REPEAT = 'Repeat'
BUTTON_ACCENT = 'Accent'
BUTTON_SCALE = 'Scale'
BUTTON_LAYOUT = 'Layout'
BUTTON_NOTE = 'Note'
BUTTON_SESSION = 'Session'
BUTTON_OCTAVE_UP = 'Octave Up'
BUTTON_OCTAVE_DOWN = 'Octave Down'
BUTTON_PAGE_LEFT = 'Page Left'
BUTTON_PAGE_RIGHT = 'Page Right'
BUTTON_SHIFT = 'Shift'
BUTTON_SELECT = 'Select'

# Push2 encoder names
# NOTE: the list of encoder names is here to facilitate autocompletion when developing apps using push2_python package, but is not needed for the package
# This list was generated using the following code:
# import json
# data = json.load(open('push2_python/Push2-map.json'))
# for item in data['Parts']['RotaryEncoders']:
#     print('ENCODER_{0} = \'{1}\''.format(item['Name'].replace(' ', '_').upper(), item['Name']))
ENCODER_TEMPO_ENCODER = 'Tempo Encoder'  # Left-most encoder
ENCODER_SWING_ENCODER = 'Swing Encoder'
ENCODER_TRACK1_ENCODER = 'Track1 Encoder'
ENCODER_TRACK2_ENCODER = 'Track2 Encoder'
ENCODER_TRACK3_ENCODER = 'Track3 Encoder'
ENCODER_TRACK4_ENCODER = 'Track4 Encoder'
ENCODER_TRACK5_ENCODER = 'Track5 Encoder'
ENCODER_TRACK6_ENCODER = 'Track6 Encoder'
ENCODER_TRACK7_ENCODER = 'Track7 Encoder'
ENCODER_TRACK8_ENCODER = 'Track8 Encoder'
ENCODER_MASTER_ENCODER = 'Master Encoder'  # Right-most encoder
