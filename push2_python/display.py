import usb.core
import usb.util
import numpy
import logging
from .classes import AbstractPush2Section
from .exceptions import Push2USBDeviceConfigurationError, Push2USBDeviceNotFound
from .constants import ABLETON_VENDOR_ID, PUSH2_PRODUCT_ID, USB_TRANSFER_TIMEOUT, DISPLAY_FRAME_HEADER, \
    DISPLAY_BUFFER_SIZE, DISPLAY_FRAME_XOR_PATTERN, DISPLAY_N_LINES, DISPLAY_LINE_PIXELS, DISPLAY_LINE_FILLER_BYTES, \
    FRAME_FORMAT_BGR565, FRAME_FORMAT_RGB565, FRAME_FORMAT_RGB

NP_DISPLAY_FRAME_XOR_PATTERN = numpy.array(DISPLAY_FRAME_XOR_PATTERN, dtype=numpy.uint16)  # Numpy array version of the constant


def rgb565_to_bgr565(rgb565_frame):
    r_filter = int('1111100000000000', 2)
    g_filter = int('0000011111100000', 2)
    b_filter = int('0000000000011111', 2)
    frame_r_filtered = numpy.bitwise_and(rgb565_frame, r_filter)
    frame_r_shifted = numpy.right_shift(frame_r_filtered, 11)  # Shift bits so R compoenent goes to the right
    frame_g_filtered = numpy.bitwise_and(rgb565_frame, g_filter)
    frame_g_shifted = frame_g_filtered  # No need to shift green, it stays in the same position
    frame_b_filtered = numpy.bitwise_and(rgb565_frame, b_filter)
    frame_b_shifted = numpy.left_shift(frame_b_filtered, 11)  # Shift bits so B compoenent goes to the left
    return frame_r_shifted + frame_g_shifted + frame_b_shifted  # Combine all channels


# Non-vectorized function for converting from rgb to bgr565
def rgb_to_bgr565(rgb_frame):
    # RGB is defined here as an 2d array with (r, g, b) tuples with values between [0.0, 1.0]
    # TODO: this is really slow, there are other ways to do this simple (similar to rgb565_to_bgr565)
    # which will work as well super fast. Need to implement that
    out_array = numpy.zeros(shape=(rgb_frame.shape[1], rgb_frame.shape[0]), dtype=numpy.uint16)
    for i in range(0, rgb_frame.shape[0]):
        for j in range(0, rgb_frame.shape[1]):
            r = rgb_frame[i][j][0]
            g = rgb_frame[i][j][1]
            b = rgb_frame[i][j][2]
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
        usb_device = None
        try:
            usb_device = usb.core.find(
                idVendor=ABLETON_VENDOR_ID, idProduct=PUSH2_PRODUCT_ID)
        except usb.core.NoBackendError:
            logging.error('No backend is available for pyusb. Please make sure \'libusb\' is installed in your system.')

        if usb_device is None:
            raise Push2USBDeviceNotFound

        device_configuration = usb_device.get_active_configuration()
        if device_configuration is None:
            usb_device.set_configuration()

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
        Depending on the input_format argument, "frame" must be a numpy array with the following characteristics:

        * for FRAME_FORMAT_BGR565: numpy array of shape 910x160 and of uint16. Each uint16 element specifies rgb
          color with the following bit position meaning: [b4 b3 b2 b1 b0 g5 g4 g3 g2 g1 g0 r4 r3 r2 r1 r0].

        * for FRAME_FORMAT_RGB565: numpy array of shape 910x160 and of uint16. Each uint16 element specifies rgb
          color with the following bit position meaning: [r4 r3 r2 r1 r0 g5 g4 g3 g2 g1 g0 b4 b3 b2 b1 b0].

        * for FRAME_FORMAT_RGB: numpy array of shape 910x160x3 with the third dimension representing rgb colors
          with separate float values for rgb channels (float values in range [0.0, 1.0]).

        Preferred format is brg565 as it requires no conversion before sending to Push2. Using brg565 is also very fast
        as color conversion is required but numpy handles it pretty well. You should be able to get frame rates higher than
        30 fps, depending on the speed of your computer. However, using the rgb format (FRAME_FORMAT_RGB) will result in very 
        long frame preparation times that can take seconds. This can be highgly optimized so it is as fast as the other formats
        but currently the library does not handle this format as nively. All numpy array elements are expected to be big endian.
        In addition to format conversion (if needed), "prepare_frame" prepares the frame to be sent to push by adding
        filler bytes and performing bitwise XOR as decribed in the Push2 specification.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#326-allocating-libusb-transfers
        """

        assert input_format in [FRAME_FORMAT_BGR565, FRAME_FORMAT_RGB565, FRAME_FORMAT_RGB], 'Invalid frame format'

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
            prepared_frame = rgb565_to_bgr565(prepared_frame)
        elif input_format == FRAME_FORMAT_BGR565:
            pass  # Nothing to do as this is already the requested format
        elif input_format == FRAME_FORMAT_RGB:
            pass  # Nothing as conversion was done before
        prepared_frame = prepared_frame.byteswap()  # Change to little endian
        prepared_frame = numpy.bitwise_xor(prepared_frame, NP_DISPLAY_FRAME_XOR_PATTERN)

        self.last_prepared_frame = prepared_frame
        return prepared_frame.byteswap().tobytes()

    def send_to_display(self, prepared_frame):
        """Sends a prepared frame to Push2 display.
        First sends frame header and then sends prepared_frame in buffers of BUFFER_SIZE.
        'prepared_frame' must be a flattened array of (DISPLAY_LINE_PIXELS + (DISPLAY_LINE_FILLER_BYTES // 2)) * DISPLAY_N_LINES 16bit BGR 565 values
        as returned by the 'Push2Display.prepare_frame' method.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#326-allocating-libusb-transfers
        """

        if self.usb_endpoint is not None:
            self.usb_endpoint.write(
                DISPLAY_FRAME_HEADER, USB_TRANSFER_TIMEOUT)

            self.usb_endpoint.write(prepared_frame, USB_TRANSFER_TIMEOUT)
            for i in range(0, len(prepared_frame), DISPLAY_BUFFER_SIZE):
                buffer_data = prepared_frame[i: i + DISPLAY_BUFFER_SIZE]
                self.usb_endpoint.write(buffer_data, USB_TRANSFER_TIMEOUT)

    def display_frame(self, frame, input_format=FRAME_FORMAT_BGR565):
        self.send_to_display(self.prepare_frame(frame, input_format=input_format))

    def display_prepared_frame(self, prepared_frame):
        self.send_to_display(prepared_frame)

    def display_last_frame(self):
        self.send_to_display(self.last_prepared_frame)
