import usb.core
import usb.util
import numpy
from .classes import AbstractPush2Section
from .exceptions import Push2USBDeviceConfigurationError, Push2USBDeviceNotFound
from .constants import ABLETON_VENDOR_ID, PUSH2_PRODUCT_ID, USB_TRANSFER_TIMEOUT, DISPLAY_FRAME_HEADER, \
    DISPLAY_BUFFER_SIZE, DISPLAY_FRAME_XOR_PATTERN, DISPLAY_N_LINES, DISPLAY_LINE_PIXELS, DISPLAY_LINE_FILLER_BYTES, \
    FRAME_FORMAT_BGR565, FRAME_FORMAT_RGB565, FRAME_FORMAT_RGB888, FRAME_FORMAT_RGB

NP_DISPLAY_FRAME_XOR_PATTERN = numpy.array(
    DISPLAY_FRAME_XOR_PATTERN)  # Numpy array version of the constant


# Utils for image format processing

def get_bit(value, n):
    """Get bit value at binary position from value"""
    return ((value >> n & 1) != 0)


def set_bit(value, n):
    """Set bit to True at given binary position in value"""
    return value | (1 << n)


def build_rgb565_to_bgr565_map():
    """Creates a dictionary with 2^16 items to allow easy conversion from rgb565 format to bgr565 format"""
    rgb565_to_bgr565_map = dict()
    rgb565_to_bgr565_bit_shifting_table = (
        (0, 11),  # r 1
        (1, 12),  # r 2
        (2, 13),  # r 3
        (3, 14),  # r 4
        (4, 15),  # r 5
        (11, 0),  # b 1
        (12, 1),  # b 2
        (13, 2),  # b 3
        (14, 3),  # b 4
        (15, 4),  # b 5
        (5, 5),   # g 1
        (6, 6),   # g 2
        (7, 7),   # g 3
        (8, 8),   # g 4
        (9, 9),   # g 5
        (10, 10),  # g 6
    )
    for rgb565_value in range(0, pow(2, 16)):
        bgr565_value = 0
        for i, j in rgb565_to_bgr565_bit_shifting_table:
            if get_bit(rgb565_value, i):
                bgr565_value = set_bit(bgr565_value, j)
        rgb565_to_bgr565_map[rgb565_value] = int(bgr565_value)
    return rgb565_to_bgr565_map


def create_vectorized_conversion_functions():
    rgb565_to_bgr565_map = build_rgb565_to_bgr565_map()
    rgb565_to_bgr565_vecotrized = numpy.vectorize(
        lambda x: rgb565_to_bgr565_map[x], otypes=[numpy.uint16])

    def rgb888_to_bgr565(rgb888_value):
        # NOTE: this code is very slow, can't be used for real-time conversion
        bgr565_value = 0
        rgb888_to_bgr565_bit_shifting_table = (
            (16, 0),  # b 1
            (17, 1),  # b 2
            (18, 2),  # b 3
            (19, 3),  # b 4
            (20, 4),  # b 5
            (8, 5),   # g 1
            (9, 6),   # g 2
            (10, 7),   # g 3
            (11, 8),   # g 4
            (12, 9),   # g 5
            (13, 10),  # g 6
            (0, 11),  # r 1
            (1, 12),  # r 2
            (2, 13),  # r 3
            (3, 14),  # r 4
            (4, 15)  # r 5
        )
        for i, j in rgb888_to_bgr565_bit_shifting_table:
            if get_bit(rgb888_value, i):
                bgr565_value = set_bit(bgr565_value, j)
        return int(bgr565_value)
    rgb888_to_bgr565_vecotrized = numpy.vectorize(
        rgb888_to_bgr565, otypes=[numpy.uint16])

    return rgb565_to_bgr565_vecotrized, rgb888_to_bgr565_vecotrized


# Vectorized functions to be used for converting from rgb565 to bgr565 and from rgb888 to bgr565
rgb565_to_bgr565_vecotrized, rgb888_to_bgr565_vecotrized = create_vectorized_conversion_functions()

# Non-vectorized function for converting from rgb to bgr565
def rgb_to_bgr565(rgb_frame):
    # RGB is defined here as an 2d array with (r, g, b) tuples with values between [0.0, 1.0]
    # NOTE: this is really slow, should only be used offline
    out_array = numpy.zeros(shape=(rgb_frame.shape[1], rgb_frame.shape[0]), dtype=numpy.uint16)
    for i in range(0, rgb_frame.shape[0]):
        for j in range(0, rgb_frame.shape[1]):
            r = rgb_frame[i][j][0]
            g = rgb_frame[i][j][0]
            b = rgb_frame[i][j][0]
            r = int(round(r * (pow(2, 5) - 1)))
            g = int(round(g * (pow(2, 6) - 1)))
            b = int(round(b * (pow(2, 5) - 1)))
            out_array[j][i] = int(
                '{b:05b}{g:06b}{r:05b}'.format(r=r, g=g, b=b), 2)
    return out_array


class Push2Display(AbstractPush2Section):
    """Class to interface with Ableton's Push2 display.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#display-interface
    """
    usb_endpoint = None
    last_prepared_frame = None

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

    def prepare_frame(self, frame, input_format=FRAME_FORMAT_BGR565):
        """Prepare the given image frame to be shown in the Push2's display.
        `frame` must be a numpy array of shape 910x160. Elements of the array represent colors in either
        brg565, rgb565, rgb888 or rgb formats. Preferred format is brg565 as it requires no conversion before sending
        to Push2. Using brg565 it should be possible to achieve frame rates as high as 60fps (and theoretically more,
        but not supported by the display itself). With rgb565 the conversion slows down the process but should still 
        allow frame rates of 26fps. Sending data in rgb888 will result in very long frame preparation times that can
        take seconds. Therefore rgb888 format should only be used for displaying static images that are prepared offline.
        Similarly, sending data with rgb format (i.e. array of shape 910x160x3 with r, g, b as floats in range [0.0, 1.0])
        also results in very long conversion times that can take seconds and should only be used for images prepared offline.
        This function expects numpy array elements to be big endian.
        In addition to format changing (if needed), this function prepares the frame to be sent to push by adding 
        filler bytes and performing bitwise XOR as decribed in the Push2 specification.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#326-allocating-libusb-transfers
        """

        assert input_format in [FRAME_FORMAT_BGR565, FRAME_FORMAT_RGB565,
                                FRAME_FORMAT_RGB888, FRAME_FORMAT_RGB], 'Invalid frame format'

        if input_format == FRAME_FORMAT_RGB:
            # If format is rgb, do conversion before the rest as frame must be reshaped
            # from (w, h, 3) to (w, h)
            frame = rgb_to_bgr565(frame)

        assert type(frame) == numpy.ndarray
        assert frame.dtype == numpy.dtype('uint16')
        assert frame.shape[0] == DISPLAY_LINE_PIXELS, 'Wrong number of pixels in line ({0})'.format(
            frame.shape[0])
        assert frame.shape[1] == DISPLAY_N_LINES, 'Wrong number of lines in frame ({0})'.format(
            frame.shape[1])

        width = DISPLAY_LINE_PIXELS + DISPLAY_LINE_FILLER_BYTES // 2
        height = DISPLAY_N_LINES
        prepared_frame = numpy.zeros(shape=(width, height), dtype=numpy.uint16)
        prepared_frame[0:frame.shape[0], 0:frame.shape[1]] = frame
        prepared_frame = prepared_frame.transpose().flatten()
        if input_format == FRAME_FORMAT_RGB565:
            prepared_frame = rgb565_to_bgr565_vecotrized(prepared_frame)
        elif input_format == FRAME_FORMAT_RGB888:
            prepared_frame = rgb888_to_bgr565_vecotrized(prepared_frame)
        elif input_format == FRAME_FORMAT_BGR565:
            pass  # Nothing to do as this is already the requested format
        elif input_format == FRAME_FORMAT_RGB:
            pass  # Nothing as conversion was done before
        prepared_frame = prepared_frame.byteswap()  # Change to little endian
        prepared_frame = numpy.bitwise_xor(prepared_frame, NP_DISPLAY_FRAME_XOR_PATTERN)

        self.last_prepared_frame = prepared_frame
        return prepared_frame

    def send_to_display(self, prepared_frame):
        """Sends frame_bytes to Push2 display.
        First sends frame header and then sends prepared_frame in buffers of BUFFER_SIZE.
        'prepared_frame' must be a flattened array of (DISPLAY_LINE_PIXELS + (DISPLAY_LINE_FILLER_BYTES // 2)) * DISPLAY_N_LINES 16bit BGR 565 values
        as returned by the 'Push2Display.prepare_frame' method.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#326-allocating-libusb-transfers
        """
        if self.usb_endpoint is not None:
            self.usb_endpoint.write(
                DISPLAY_FRAME_HEADER, USB_TRANSFER_TIMEOUT)

            for i in range(0, len(prepared_frame), DISPLAY_BUFFER_SIZE):
                buffer_data = prepared_frame[i: i + DISPLAY_BUFFER_SIZE]
                self.usb_endpoint.write(buffer_data, USB_TRANSFER_TIMEOUT)

    def display_frame(self, frame, input_format=FRAME_FORMAT_BGR565):
        self.send_to_display(self.prepare_frame(frame, input_format=input_format))

    def display_last_frame(self):
        self.send_to_display(self.last_prepared_frame)
