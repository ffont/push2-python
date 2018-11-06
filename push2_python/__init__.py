import usb.core
import usb.util
import logging
import sys
import mido
from collections import defaultdict
from .exceptions import Push2USBDeviceNotFound, Push2USBDeviceConfigurationError, Push2MIDIeviceNotFound
from .display import Push2Display
from .pads import Push2Pads
from .touchstrip import Push2TouchStrip
from .constants import PUSH2_MIDI_IN_PORT_NAME, PUSH2_MIDI_OUT_PORT_NAME

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

action_handler_registry = defaultdict(list)


class Push2(object):
    """Class to interface with Ableton's Push2.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc
    """
    midi_in_port = None
    midi_out_port = None
    display = None
    pads = None
    touchtrip = None

    def __init__(self):

        # Init Display
        self.display = Push2Display(self)
        try:
            self.display.configure_usb_device()
        except (Push2USBDeviceNotFound, Push2USBDeviceConfigurationError) as e:
            logging.error('Could not initialize Push 2 Display: {0}'.format(e))

        # Init individual sections
        self.pads = Push2Pads(self)
        self.touchtrip = Push2TouchStrip(self)

        # Configure MIDI ports
        try:
            self.configure_midi_ports()
            self.midi_in_port.callback = self.on_midi_message
        except (Push2MIDIeviceNotFound) as e:
            logging.error('Could not initialize Push 2 Pads: {0}'.format(e))

    def trigger_action(self, *args, **kwargs):
        action_name = args[0]
        new_args = [self] + list(args[1:])
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
        self.touchtrip.on_midi_message(message)

        logging.debug('Received MIDI message from Push: {0}'.format(message))


def action_handler(action_name):
    """
    TODO: document this
    """
    def wrapper(func):
        logging.debug('Registered handler {0} for action {1}'.format(func, action_name))
        action_handler_registry[action_name].append(func)
        return func
    return wrapper
