# USB device/transfer settings
ABLETON_VENDOR_ID = 0x2982
PUSH2_PRODUCT_ID = 0x1967
USB_TRANSFER_TIMEOUT = 1000

# MIDI
PUSH2_MIDI_OUT_PORT_NAME = 'Ableton Push 2 Live Port'
PUSH2_MIDI_IN_PORT_NAME = 'Ableton Push 2 User Port'  # TODO: might use Live port as well?

# Push 2 Display
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

# LEDS
RGB_COLORS = {
    'black': 0,
    'white': 122,
    'light_gray': 123,
    'dark_gray': 124,
    'blue': 125,
    'green': 126,
    'red': 127,
}
RGB_DEFAULT_COLOR = 0

ANIMATIONS = {  # TODO: animations only work when MIDI clock data is sent (which is not so far)
    'static': 0,
    'blinking': 14
}
ANIMATIONS_DEFAULT = 0
