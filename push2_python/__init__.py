import usb.core
import usb.util
import logging
import sys
import mido
import json
from collections import defaultdict
from .exceptions import Push2USBDeviceNotFound, Push2USBDeviceConfigurationError, Push2MIDIeviceNotFound
from .display import Push2Display
from .pads import Push2Pads
from .buttons import Push2Buttons, get_individual_button_action_name
from .touchstrip import Push2TouchStrip
from .constants import PUSH2_MIDI_IN_PORT_NAME, PUSH2_MIDI_OUT_PORT_NAME, PUSH2_MAP_FILE_PATH, ACTION_BUTTON_PRESSED, \
    ACTION_BUTTON_RELEASED, ACTION_TOUCHSTRIP_TOUCHED, ACTION_PAD_PRESSED, ACTION_PAD_RELEASED, ACTION_PAD_AFTERTOUCH

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

action_handler_registry = defaultdict(list)


class Push2(object):
    """Class to interface with Ableton's Push2.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc
    """
    midi_in_port = None
    midi_out_port = None
    push2_map = None
    display = None
    pads = None
    buttons = None
    touchtrip = None
    

    def __init__(self):

        # Load Push2 map from JSON file provided in Push2's interface doc
        # https://github.com/Ableton/push-interface/blob/master/doc/Push2-map.json
        self.push2_map = json.load(open(PUSH2_MAP_FILE_PATH))

        # Init Display
        self.display = Push2Display(self)
        try:
            self.display.configure_usb_device()
        except (Push2USBDeviceNotFound, Push2USBDeviceConfigurationError) as e:
            logging.error('Could not initialize Push 2 Display: {0}'.format(e))

        # Configure MIDI ports
        try:
            self.configure_midi_ports()
            self.midi_in_port.callback = self.on_midi_message
        except (Push2MIDIeviceNotFound) as e:
            logging.error('Could not initialize Push 2 MIDI: {0}'.format(e))

        # Init individual sections
        self.pads = Push2Pads(self)
        self.buttons = Push2Buttons(self)
        self.touchtrip = Push2TouchStrip(self)

    def trigger_action(self, *args, **kwargs):
        action_name = args[0]
        new_args = [self]
        if len(args) > 1:
            new_args += list(args[1:])
        for action, func in action_handler_registry.items():
            if action == action_name:
                func[0](*new_args, **kwargs)  # TODO: why is func a 1-element list?

    def configure_midi_ports(self):
        try:
            self.midi_in_port = mido.open_input(PUSH2_MIDI_IN_PORT_NAME)
            self.midi_out_port = mido.open_output(PUSH2_MIDI_OUT_PORT_NAME)
        except OSError:
            raise Push2MIDIeviceNotFound

    def send_midi_to_push(self, msg):
        if self.midi_out_port is not None:
            self.midi_out_port.send(msg)

    def on_midi_message(self, message):
        """Handle incomming MIDI messages from Push.
        Call `on_midi_nessage` of each individual section.
        TODO: we could add a bit of logic here to interpret MIDI messages and only
        call the `on_midi_nessage` method of the correspoidng section."""
        self.pads.on_midi_message(message)
        self.buttons.on_midi_message(message)
        self.touchtrip.on_midi_message(message)

        logging.debug('Received MIDI message from Push: {0}'.format(message))


def action_handler(action_name, button_name=None):
    """
    Generic action handler decorator used by other specific decorators.
    This decorator should not be used directly. Specific decorators for individual actions should be used instead.
    """
    def wrapper(func):
        action = action_name
        if (action_name == ACTION_BUTTON_PRESSED or action_name == ACTION_BUTTON_RELEASED) and button_name is not None:
            # If the action is pressing or releasing a button and a spcific button name was given,
            # include the button name in the action name so that it can be triggered individually
            action = get_individual_button_action_name(action_name, button_name)
        logging.debug('Registered handler {0} for action {1}'.format(func, action))
        action_handler_registry[action].append(func)
        return func
    return wrapper


def on_button_pressed(button_name=None):
    """Shortcut for registering handlers for ACTION_BUTTON_PRESSED events.
    Optional "button_name" argument is to link the handler to a specific button.
    Functions decorated by this decorator will receive the Push2 object instance
    as the first argument and the button name as second argument if it was not
    already specified in the decorator. Examples:

    @push2_python.on_button_pressed()
    def function(push, button_name):
        print('Button', button_name, 'pressed')

    @push2_python.on_button_pressed(push2_python.constants.BUTTON_1_16)
    def function(push):
        print('Button 1/6 pressed')
    """
    return action_handler(ACTION_BUTTON_PRESSED, button_name=button_name)


def on_button_released(button_name=None):
    """Shortcut for registering handlers for ACTION_BUTTON_RELEASED events.
    Optional "button_name" argument is to link the handler to a specific button.
    Functions decorated by this decorator will receive the Push2 object instance
    as the first argument and the button name as second argument if it was not
    already specified in the decorator. Examples:

    @push2_python.on_button_released()
    def function(push, button_name):
        print('Button', button_name, 'released')

    @push2_python.on_button_released(push2_python.constants.BUTTON_1_16)
    def function(push):
        print('Button 1/6 released')
    """
    return action_handler(ACTION_BUTTON_RELEASED, button_name=button_name)


def on_touchstrip():
    """Shortcut for registering handlers for ACTION_TOUCHSTRIP_TOUCHED events.
    Functions decorated by this decorator will receive the Push2 object instance
    as the first argument and a pitchbend value as the second aegument. Examples:

    @push2_python.on_touchstrip()
    def function(push, value):
        print('Touchstrip touched with value', value)
    """
    return action_handler(ACTION_TOUCHSTRIP_TOUCHED)


def on_pad_pressed():
    """Shortcut for registering handlers for ACTION_PAD_PRESSED events.
    Functions decorated by this decorator will receive the Push2 object instance
    as the first argument, the pad number as the second argument, the pad (i,j)
    coordinates as the third argument, and the velocity with which the pad was
    pressed as the fourth argument. Examples:

    @push2_python.on_pad_pressed()
    def function(push, pad_n, pad_ij, velocity):
        print('Pad', pad_n, 'pressed with velocity', velocity)
    """
    return action_handler(ACTION_PAD_PRESSED)


def on_pad_released():
    """Shortcut for registering handlers for ACTION_PAD_RELEASED events.
    Functions decorated by this decorator will receive the Push2 object instance
    as the first argument, the pad number as the second argument, the pad (i,j)
    coordinates as the third argument, and the velocity with which the pad was
    released as the fourth argument. Examples:

    @push2_python.on_pad_released()
    def function(push, pad_n, pad_ij, velocity):
        print('Pad', pad_n, 'released with velocity', velocity)
    """
    return action_handler(ACTION_PAD_RELEASED)


def on_pad_aftertouch():
    """Shortcut for registering handlers for ACTION_PAD_AFTERTOUCH events.
    Functions decorated by this decorator will receive the Push2 object instance
    as the first argument, the pad number as the second argument, the pad (i,j)
    coordinates as the third argument, and the current aftertouch (velocity) value
    as the fourth argument. Examples:

    @push2_python.on_pad_aftertouch()
    def function(push, pad_n, pad_ij, velocity):
        print('Pad', pad_n, 'released with velocity', velocity)
    """
    return action_handler(ACTION_PAD_AFTERTOUCH)
