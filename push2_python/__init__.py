import usb.core
import usb.util
import logging
import sys
import mido
from .exceptions import Push2USBDeviceNotFound, Push2USBDeviceConfigurationError, Push2MIDIeviceNotFound
from .display import Push2Display
from .pads import Push2Pads
from .constants import PUSH2_MIDI_IN_PORT_NAME, PUSH2_MIDI_OUT_PORT_NAME
from .classes import Push2DebugView

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


class Push2(object):
    """Class to interface with Ableton's Push2.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc
    """
    midi_in_port = None
    midi_out_port = None
    display = None
    pads = None
    active_views = None

    def __init__(self):

        # Add debug view to active views
        self.active_views = [Push2DebugView]

        # Init Display
        self.display = Push2Display(self)
        try:
            self.display.configure_usb_device()
        except (Push2USBDeviceNotFound, Push2USBDeviceConfigurationError) as e:
            logging.debug('Could not initialize Push 2 Display: {0}'.format(e))

        # Init Pads
        self.pads = Push2Pads(self)

        # Configure MIDI ports
        try:
            self.configure_midi_ports()
            self.midi_in_port.callback = self.on_midi_message
        except (Push2MIDIeviceNotFound) as e:
            logging.debug('Could not initialize Push 2 Pads: {0}'.format(e))

    def trigger_on_view(self, *args, **kwargs):
        method_name = args[0]
        new_args = args[1:]
        for view in self.active_views:
            getattr(view, method_name)(*new_args, **kwargs)

    def configure_midi_ports(self):
        try:
            self.midi_in_port = mido.open_input(PUSH2_MIDI_IN_PORT_NAME)
            self.midi_out_port = mido.open_output(PUSH2_MIDI_OUT_PORT_NAME)
        except OSError:
            raise Push2MIDIeviceNotFound

    def on_midi_message(self, message):
        """Handle incomming MIDI messages from Push.
        Call `on_midi_nessage` of each individual section.
        TODO: we could add a bit of logic here to interpret MIDI messages and only
        call the `on_midi_nessage` method of the correspoidng section."""
        self.pads.on_midi_message(message)

