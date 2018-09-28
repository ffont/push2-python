import usb.core
import usb.util

# USB device/transfer settings
ABLETON_VENDOR_ID = 0x2982
PUSH2_PRODUCT_ID = 0x1967
USB_TRANSFER_TIMEOUT = 1000

# Display settings
DISPLAY_FRAME_HEADER = [0xff, 0xcc, 0xaa, 0x88,
                        0x00, 0x00, 0x00, 0x00,
                        0x00, 0x00, 0x00, 0x00,
                        0x00, 0x00, 0x00, 0x00]
DISPLAY_XOR_PATTERN = [0xE7, 0xF3, 0xE7, 0xFF]
DISPLAY_N_LINES = 160
DISPLAY_LINE_PIXELS = 960
DISPLAY_PIXEL_BYTES = 2  # bytes
DISPLAY_LINE_FILLER_BYTES = 128
DISPLAY_LINE_SIZE = DISPLAY_LINE_PIXELS * \
    DISPLAY_PIXEL_BYTES + DISPLAY_LINE_FILLER_BYTES
DISPLAY_N_LINES_PER_BUFFER = 8
DISPLAY_BUFFER_SIZE = DISPLAY_LINE_SIZE * DISPLAY_N_LINES_PER_BUFFER


class Push2USBDeviceNotFound(Exception):
    pass


class Push2USBDeviceConfigrationError(Exception):
    pass


class Push2USBDeviceNotAvailable(Exception):
    pass


class Push2IncorrectFrameFormat(Exception):
    pass


class Push2(object):
    """Class to interface with Ableton's Push2.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc
    """
    display_usb_endpoint = None
    last_frame_bytes = None

    def __init__(self):
        self.configure_usb_device()

    def configure_usb_device(self):
        """Connect to Push2 USB device and get the Endpoint object used to send data
        to Push2's display.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#31-usb-display-interface-access
        """
        usb_device = usb.core.find(idVendor=ABLETON_VENDOR_ID, idProduct=PUSH2_PRODUCT_ID)

        if usb_device is None:
            raise Push2USBDeviceNotFound  

        usb_device.set_configuration()
        device_configuration = usb_device.get_active_configuration()
        interface = device_configuration[(0, 0)]
        out_endpoint = usb.util.find_descriptor(
            interface,
            custom_match=lambda e: \
            usb.util.endpoint_direction(e.bEndpointAddress) == \
            usb.util.ENDPOINT_OUT)

        if out_endpoint is None:
            raise Push2USBDeviceConfigrationError

        self.display_usb_endpoint = out_endpoint

    @staticmethod
    def rgb_to_display_pixel_bytes(r, g, b):
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
        if self.display_usb_endpoint is None:
            raise Push2USBDeviceNotAvailable

        self.display_usb_endpoint.write(
            DISPLAY_FRAME_HEADER, USB_TRANSFER_TIMEOUT)

        for i in range(0, len(frame_bytes), DISPLAY_BUFFER_SIZE):
            buffer_data = [byte ^ DISPLAY_XOR_PATTERN[count % len(DISPLAY_XOR_PATTERN)] for count,
                           byte in enumerate(frame_bytes[i: i + DISPLAY_BUFFER_SIZE])]
            self.display_usb_endpoint.write(
                buffer_data, USB_TRANSFER_TIMEOUT)

    def display_frame(self, frame):
        """Show the given frame in the Push2 display.
        `frame` must be a multidimensional list (of iterable type) of size 160 * 960 * 3.
        That is Push2's screen size with 160 lines and 960 pixels per line. Each pixel color
        must be specified with a list of 3 RGB values in the range [0.0, 1.0].
        """
        assert len(frame) == DISPLAY_N_LINES, 'Wrong number of lines in frame ({0})'.format(len(frame))
            
        frame_bytes = []
        for line in frame:
            assert len(line) == DISPLAY_LINE_PIXELS, 'Wrong number of pixels in line ({0})'.format(len(line))
            for pixel in line:
                assert len(pixel) == 3, 'Pixel must have 3 values'
                frame_bytes += self.rgb_to_display_pixel_bytes(*pixel)
            for _ in range(0, DISPLAY_LINE_FILLER_BYTES):
                frame_bytes += (0b00000000,)

        self.last_frame_bytes = frame_bytes
        self.send_to_display(frame_bytes)

    def display_last_frame(self):
        self.send_to_display(self.last_frame_bytes)
