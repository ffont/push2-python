import usb.core
import usb.util
from .exceptions import Push2USBDeviceConfigurationError, Push2USBDeviceNotFound
from .constants import ABLETON_VENDOR_ID, PUSH2_PRODUCT_ID, USB_TRANSFER_TIMEOUT, DISPLAY_FRAME_HEADER, \
    DISPLAY_BUFFER_SIZE, DISPLAY_XOR_PATTERN, DISPLAY_N_LINES, DISPLAY_LINE_PIXELS, DISPLAY_LINE_FILLER_BYTES


class Push2Display(object):
    """Class to interface with Ableton's Push2 display.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#display-interface
    """
    usb_endpoint = None
    last_frame_bytes = None

    def configure_usb_device(self):
        """Connect to Push2 USB device and get the Endpoint object used to send data
        to Push2's display.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#31-usb-display-interface-access
        """
        usb_device = usb.core.find(
            idVendor=ABLETON_VENDOR_ID, idProduct=PUSH2_PRODUCT_ID)

        if usb_device is None:
            raise Push2USBDeviceNotFound

        usb_device.set_configuration()
        device_configuration = usb_device.get_active_configuration()
        interface = device_configuration[(0, 0)]
        out_endpoint = usb.util.find_descriptor(
            interface,
            custom_match=lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress) ==
            usb.util.ENDPOINT_OUT)

        if out_endpoint is None:
            raise Push2USBDeviceConfigurationError

        self.usb_endpoint = out_endpoint

    @staticmethod
    def rgb_to_pixel_bytes(r, g, b):
        """Returns the 2 bytes represeting a pixel's RGB components given
        RGB values in the range [0.0, 1.0]. 
        Return bytes in correct endianess according to specification.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#322-pixel-data
        """

        def clamp(value, minv, maxv):
            return max(minv, min(value, maxv))

        r = clamp(int(round(r * (pow(2, 5) - 1))), 0, pow(2, 5))
        g = clamp(int(round(g * (pow(2, 6) - 1))), 0, pow(2, 6))
        b = clamp(int(round(b * (pow(2, 5) - 1))), 0, pow(2, 5))
        byte_string = '{b:05b}{g:06b}{r:05b}'.format(r=r, g=g, b=b)

        return (int(byte_string[8:], 2), int(byte_string[:8], 2))

    def send_to_display(self, frame_bytes):
        """Sends frame_bytes to Push2 display.
        First sends frame header and then sends frame_bytes in buffers of BUFFER_SIZE.
        XORs pixel data according to specification.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#326-allocating-libusb-transfers
        """
        if self.usb_endpoint is not None:
            self.usb_endpoint.write(
                DISPLAY_FRAME_HEADER, USB_TRANSFER_TIMEOUT)

            # TODO: the XOR operation below can probably be optimized to avoid iterating all buffer
            for i in range(0, len(frame_bytes), DISPLAY_BUFFER_SIZE):
                buffer_data = [byte ^ DISPLAY_XOR_PATTERN[count % len(DISPLAY_XOR_PATTERN)] for count,
                                byte in enumerate(frame_bytes[i: i + DISPLAY_BUFFER_SIZE])]
                self.usb_endpoint.write(
                    buffer_data, USB_TRANSFER_TIMEOUT)

    def display_frame(self, frame):
        """Show the given frame in the Push2 display.
        `frame` must be a multidimensional list (of iterable type) of size 160 * 960 * 3.
        That is Push2's screen size with 160 lines and 960 pixels per line. Each pixel color
        must be specified with a list of 3 RGB values in the range [0.0, 1.0].
        """
        # TODO: the operations below could probably be optimized by using numpy arrays, this implementation is really slow
        assert len(frame) == DISPLAY_N_LINES, 'Wrong number of lines in frame ({0})'.format(
            len(frame))
        frame_bytes = []
        for line in frame:
            assert len(line) == DISPLAY_LINE_PIXELS, 'Wrong number of pixels in line ({0})'.format(
                len(line))
            for pixel in line:
                assert len(pixel) == 3, 'Pixel must have 3 values'
                frame_bytes += self.rgb_to_pixel_bytes(*pixel)
            for _ in range(0, DISPLAY_LINE_FILLER_BYTES):
                frame_bytes += (0b00000000,)

        self.last_frame_bytes = frame_bytes
        self.send_to_display(frame_bytes)

    def display_last_frame(self):
        self.send_to_display(self.last_frame_bytes)
