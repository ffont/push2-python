import usb.core
import usb.util
import logging
import sys
from .exceptions import Push2USBDeviceNotFound, Push2USBDeviceConfigurationError, Push2MIDIeviceNotFound
from .display import Push2Display
from .pads import Push2Pads

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


class Push2(object):
    """Class to interface with Ableton's Push2.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc
    """
    display = None
    pads = None

    def __init__(self):

        # Init Display
        self.display = Push2Display()
        try:
            self.display.configure_usb_device()
        except (Push2USBDeviceNotFound, Push2USBDeviceConfigurationError) as e:
            logging.debug('Could not initialize Push 2 Display: {0}'.format(e))

        # Init Pads
        self.pads = Push2Pads()
        try:
            self.pads.configure_midi_ports()
        except (Push2MIDIeviceNotFound) as e:
            logging.debug('Could not initialize Push 2 Pads: {0}'.format(e))


