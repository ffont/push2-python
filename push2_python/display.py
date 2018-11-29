import usb.core
import usb.util
import numpy
from .classes import AbstractPush2Section
from .exceptions import Push2USBDeviceConfigurationError, Push2USBDeviceNotFound
from .constants import ABLETON_VENDOR_ID, PUSH2_PRODUCT_ID, USB_TRANSFER_TIMEOUT, DISPLAY_FRAME_HEADER, \
    DISPLAY_BUFFER_SIZE, DISPLAY_FRAME_XOR_PATTERN, DISPLAY_N_LINES, DISPLAY_LINE_PIXELS, DISPLAY_LINE_FILLER_BYTES

NP_DISPLAY_FRAME_XOR_PATTERN = numpy.array(
    DISPLAY_FRAME_XOR_PATTERN)  # Numpy array version of the constant


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

    @staticmethod
    def rgb_to_pixel_bytes(r, g, b):
        """Returns the 2 bytes represeting a pixel's RGB components given
        RGB values in the range [0.0, 1.0]. 
        Return bytes in correct endianess according to specification.
        NOTE: this function is provided as a utility funtion for testing purposes only
        or for when speed is not requited. It is very slow and should not be used for creating images in real time.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#322-pixel-data
        """

        def clamp(value, minv, maxv):
            return max(minv, min(value, maxv))

        r = clamp(int(round(r * (pow(2, 5) - 1))), 0, pow(2, 5))
        g = clamp(int(round(g * (pow(2, 6) - 1))), 0, pow(2, 6))
        b = clamp(int(round(b * (pow(2, 5) - 1))), 0, pow(2, 5))
        byte_string = '{b:05b}{g:06b}{r:05b}'.format(r=r, g=g, b=b)

        return (int(byte_string[8:], 2), int(byte_string[:8], 2))

    def prepare_frame(self, frame):
        """Show the given frame in the Push2 display.
        `frame` must be a numpy array of shape 910x160 and uint16 values representing 16 bit colors in BRG 565 format.
        That is Push2's screen size with 160 lines and 960 pixels per line. Each pixel represented as 16 bit value.
        This function prepares the frame to be sent to push by adding 0 filler bytes and performing bitwise XOR as
        decribed in the Push2 specification.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#326-allocating-libusb-transfers
        """

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
        prepared_frame = prepared_frame.flatten()
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

    def display_frame(self, frame):
        self.send_to_display(self.prepare_frame(frame))

    def display_last_frame(self):
        self.send_to_display(self.last_prepared_frame)
