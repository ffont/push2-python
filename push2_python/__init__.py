import usb.core
import usb.util
import logging
import sys
import mido
from collections import defaultdict
from .exceptions import Push2USBDeviceNotFound, Push2USBDeviceConfigurationError, Push2MIDIeviceNotFound
from .display import Push2Display
from .pads import Push2Pads, get_individual_pad_action_name
from .buttons import Push2Buttons, get_individual_button_action_name
from .encoders import Push2Encoders, get_individual_encoder_action_name
from .touchstrip import Push2TouchStrip
from .push2_map import push2_map
from .constants import PUSH2_USER_PORT_NAME, PUSH2_LIVE_PORT_NAME, PUSH2_MAP_FILE_PATH, ACTION_BUTTON_PRESSED, \
    ACTION_BUTTON_RELEASED, ACTION_TOUCHSTRIP_TOUCHED, ACTION_PAD_PRESSED, ACTION_PAD_RELEASED, ACTION_PAD_AFTERTOUCH, \
    ACTION_ENCODER_ROTATED, ACTION_ENCODER_TOUCHED, ACTION_ENCODER_RELEASED

logging.basicConfig(stream=sys.stdout, level=logging.ERROR)

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
    encoders = None
    touchtrip = None


    def __init__(self, use_user_midi_port=False):
        """Initializes object to interface with Ableton's Push2.
        This function will set up USB and MIDI connections with the hardware device.
        By default, MIDI connection will use LIVE MIDI port instead of USER MIDI port.
        USER MIDI port can be configured using the argument 'use_user_midi_port'.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc
        """

        # Load Push2 map from JSON file provided in Push2's interface doc
        # https://github.com/Ableton/push-interface/blob/master/doc/Push2-map.json
        self.push2_map = push2_map

        # Init Display
        self.display = Push2Display(self)
        try:
            self.display.configure_usb_device()
        except (Push2USBDeviceNotFound, Push2USBDeviceConfigurationError) as e:
            logging.error('Could not initialize Push 2 Display: {0}'.format(e))

        # Configure MIDI ports
        try:
            self.configure_midi_ports(use_user_midi_port=use_user_midi_port)
            self.midi_in_port.callback = self.on_midi_message
        except (Push2MIDIeviceNotFound) as e:
            logging.error('Could not initialize Push 2 MIDI: {0}'.format(e))

        # Init individual sections
        self.pads = Push2Pads(self)
        self.buttons = Push2Buttons(self)
        self.encoders = Push2Encoders(self)
        self.touchtrip = Push2TouchStrip(self)

    def trigger_action(self, *args, **kwargs):
        action_name = args[0]
        new_args = [self]
        if len(args) > 1:
            new_args += list(args[1:])
        for action, func in action_handler_registry.items():
            if action == action_name:
                func[0](*new_args, **kwargs)  # TODO: why is func a 1-element list?

    def configure_midi_ports(self, use_user_midi_port=False):
        port_name = PUSH2_USER_PORT_NAME if use_user_midi_port else PUSH2_LIVE_PORT_NAME
        try:
            self.midi_in_port = mido.open_input(port_name)
            self.midi_out_port = mido.open_output(port_name)
        except OSError:
            raise Push2MIDIeviceNotFound

    def send_midi_to_push(self, msg):
        if self.midi_out_port is not None:
            self.midi_out_port.send(msg)

    def on_midi_message(self, message):
        """Handle incomming MIDI messages from Push.
        Call `on_midi_nessage` for each individual section.
        """
        self.pads.on_midi_message(message)
        self.buttons.on_midi_message(message)
        self.encoders.on_midi_message(message)
        self.touchtrip.on_midi_message(message)

        logging.debug('Received MIDI message from Push: {0}'.format(message))


def action_handler(action_name, button_name=None, pad_n=None, pad_ij=None, encoder_name=None):
    """
    Generic action handler decorator used by other specific decorators.
    This decorator should not be used directly. Specific decorators for individual actions should be used instead.
    """
    def wrapper(func):
        action = action_name
        if action_name in [ACTION_BUTTON_PRESSED, ACTION_BUTTON_RELEASED] and button_name is not None:
            # If the action is pressing or releasing a button and a spcific button name is given,
            # include the button name in the action name so that it can be triggered individually
            action = get_individual_button_action_name(action_name, button_name)
        if action_name in [ACTION_PAD_PRESSED, ACTION_PAD_RELEASED, ACTION_PAD_AFTERTOUCH] and (pad_n is not None or pad_ij is not None):
            # If the action is pressing, releasing or aftertouching a pad and a spcific pad number or
            # pad ij coordinates are given name was given, include the pad name or cordinate in the
            # action name so that it can be triggered individually
            action = get_individual_pad_action_name(action_name, pad_n=pad_n, pad_ij=pad_ij)
        if action_name in [ACTION_ENCODER_ROTATED, ACTION_ENCODER_TOUCHED, ACTION_ENCODER_RELEASED] and encoder_name is not None:
            # If the action is rotating, touching or releasing a rotatory encoder and a specific encoder
            # name is given, include the encoder name in the action name so that it can be triggered individually
            action = get_individual_encoder_action_name(action_name, encoder_name=encoder_name)
        logging.debug('Registered handler {0} for action {1}'.format(func, action))
        action_handler_registry[action].append(func)
        return func
    return wrapper


def on_button_pressed(button_name=None):
    """Shortcut for registering handlers for ACTION_BUTTON_PRESSED events.
    Optional "button_name" argument is to link the handler to a specific button.
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Button name (string, only if button name not specified in decorator)

    Examples:

    @push2_python.on_button_pressed()
    def function(push, button_name):
        print('Button', button_name, 'pressed')

    @push2_python.on_button_pressed(push2_python.constants.BUTTON_1_16)
    def function(push):
        print('Button 1/16 pressed')
    """
    return action_handler(ACTION_BUTTON_PRESSED, button_name=button_name)


def on_button_released(button_name=None):
    """Shortcut for registering handlers for ACTION_BUTTON_RELEASED events.
    Optional "button_name" argument is to link the handler to a specific button.
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Button name (string, only if button name not specified in decorator)

   Examples:

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
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Touchstrip value (int)

    Examples:

    @push2_python.on_touchstrip()
    def function(push, value):
        print('Touchstrip touched with value', value)
    """
    return action_handler(ACTION_TOUCHSTRIP_TOUCHED)


def on_pad_pressed(pad_n=None, pad_ij=None):
    """Shortcut for registering handlers for ACTION_PAD_PRESSED events.
    Optional "pad_n" or "pad_ij" arguments are to link the handler to a specific pad.
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Pad number (int, only if pad not specified in decorator)
        * Pad ij coordinates (tuple, only if pad not specified in decorator)
        * Velocity value (int 0-127)

    Examples:

    @push2_python.on_pad_pressed()
    def function(push, pad_n, pad_ij, velocity):
        print('Pad', pad_n, 'pressed with velocity', velocity)

    @push2_python.on_pad_pressed(pad_n=36)
    def function(push, velocity):
        print('Pad 36 pressed with velocity', velocity)

    @push2_python.on_pad_pressed(pad_ij=(0,3))
    def function(push, velocity):
        print('Pad (0, 3) pressed with velocity', velocity)
    """
    return action_handler(ACTION_PAD_PRESSED, pad_n=pad_n, pad_ij=pad_ij)


def on_pad_released(pad_n=None, pad_ij=None):
    """Shortcut for registering handlers for ACTION_PAD_RELEASED events.
    Optional "pad_n" or "pad_ij" arguments are to link the handler to a specific pad.
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Pad number (int, only if pad not specified in decorator)
        * Pad ij coordinates (tuple, only if pad not specified in decorator)
        * Release velocity value (int 0-127)

    Examples:

    @push2_python.on_pad_released()
    def function(push, pad_n, pad_ij, velocity):
        print('Pad', pad_n, 'released with velocity', velocity)

    @push2_python.on_pad_released(pad_n=36)
    def function(push, velocity):
        print('Pad 36 released with velocity', velocity)

    @push2_python.on_pad_released(pad_ij=(0,3))
    def function(push, velocity):
        print('Pad (0, 3) released with velocity', velocity)
    """
    return action_handler(ACTION_PAD_RELEASED, pad_n=pad_n, pad_ij=pad_ij)


def on_pad_aftertouch(pad_n=None, pad_ij=None):
    """Shortcut for registering handlers for ACTION_PAD_AFTERTOUCH events. This can
    work in "channel aftertouch" (cAT) or "polyphonic aftertouch" (polyAT) modes, which
    are configured using "set_polyphonic_aftertouch" or "set_channel_aftertouch" methods
    in Push2.pads. cAT mode is enabled by default. In polyAT mode Push will send individual
    aftertouch data for each pad, while in cAT mode aftertouch value will be shared for
    all pads. In polyAT mode, optional "pad_n" or "pad_ij" arguments can be passed to the
    decorator to link the handler to a specific pad adftertouch action.
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Pad number (int, only if pad not specified in decorator, will be none in cAT mode)
        * Pad ij position (tuple, only if pad not specified in decorator, will be none in cAT mode)
        * Aftertouch value (int 0-127)

    Examples:

    @push2_python.on_pad_aftertouch()
    def function(push, pad_n, pad_ij, value):
        if pad_n is not None:
            print('Pad', pad_n, 'aftertouch with value', value)
        else:
            print('Channel aftertouch with value', value)

    @push2_python.on_pad_aftertouch(pad_n=36)
    def function(push, value):
        print('Pad 36 aftertouched with value', value)

    @push2_python.on_pad_aftertouch(pad_ij=(0,3))
    def function(push, value):
        print('Pad (0, 3) aftertouched with value', value)
    """
    return action_handler(ACTION_PAD_AFTERTOUCH, pad_n=pad_n, pad_ij=pad_ij)


def on_encoder_rotated(encoder_name=None):
    """Shortcut for registering handlers for ACTION_ENCODER_ROTATED events.
    Optional "encoder_name" argument is to link the handler to a specific encoder.
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Encoder name (string, only if pad not specified in decorator)
        * Encoder increment (int, 1 for clockwise rotation and -1 for counter-clockwise)

    Examples:

    @push2_python.on_encoder_rotated()
    def function(push, encoder_name, increment):
        print('Encoder', encoder_name, 'rotated with increment', increment)

    @push2_python.on_encoder_rotated(push2_python.constants.ENCODER_TRACK1_ENCODER)
    def function(push, increment):
        print('Encoder for Track 1 rotated with increment', increment)
    """
    return action_handler(ACTION_ENCODER_ROTATED, encoder_name=encoder_name)


def on_encoder_touched(encoder_name=None):
    """Shortcut for registering handlers for ACTION_ENCODER_TOUCHED events.
    Optional "encoder_name" argument is to link the handler to a specific encoder.
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Encoder name (string, only if pad not specified in decorator)

    Examples:

    @push2_python.on_encoder_touched()
    def function(push, encoder_name):
        print('Encoder', encoder_name, 'touched')

    @push2_python.on_encoder_touched(push2_python.constants.ENCODER_TRACK1_ENCODER)
    def function(push):
        print('Encoder for Track 1 touched')
    """
    return action_handler(ACTION_ENCODER_TOUCHED, encoder_name=encoder_name)


def on_encoder_released(encoder_name=None):
    """Shortcut for registering handlers for ACTION_ENCODER_RELEASED events.
    Optional "encoder_name" argument is to link the handler to a specific encoder.
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Encoder name (string, only if pad not specified in decorator)

    Examples:

    @push2_python.on_encoder_released()
    def function(push, encoder_name):
        print('Encoder', encoder_name, 'released')

    @push2_python.on_encoder_released(push2_python.constants.ENCODER_TRACK1_ENCODER)
    def function(push):
        print('Encoder for Track 1 released')
    """
    return action_handler(ACTION_ENCODER_RELEASED, encoder_name=encoder_name)
