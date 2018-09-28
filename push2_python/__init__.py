import usb.core
import usb.util
import logging
import sys
from .exceptions import Push2USBDeviceNotFound, Push2USBDeviceConfigurationError
from .display import Push2Display

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


class Push2(object):
    """Class to interface with Ableton's Push2.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc
    """
    display = None

    def __init__(self):
        self.display = Push2Display()
        try:
            self.display.configure_usb_device()
        except (Push2USBDeviceNotFound, Push2USBDeviceConfigurationError) as e:
            logging.debug('Could not initialize Push 2 Display')
