import mido
from .constants import PUSH2_MIDI_IN_PORT_NAME, PUSH2_MIDI_OUT_PORT_NAME, RGB_COLORS, RGB_DEFAULT_COLOR, ANIMATIONS, ANIMATIONS_DEFAULT
from .exceptions import Push2MIDIeviceNotFound


class Push2Pads(object):
    """Class to interface with Ableton's Push2 pads.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#Pads
    """

    midi_in_port = None
    midi_out_port = None

    def configure_midi_ports(self):
        try:
            self.midi_in_port = mido.open_input(PUSH2_MIDI_IN_PORT_NAME)
            self.midi_out_port = mido.open_output(PUSH2_MIDI_OUT_PORT_NAME)
        except OSError:
            raise Push2MIDIeviceNotFound

    def coords_to_pad_midi_number(self, i, j):
        """Transform (i, j) coordinates to the corresponding pad number
        according to the specification. (0, 0) corresponds to the top-left pad while
        (7, 7) corresponds to the bottom right pad.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#23-midi-mapping
        """
        
        def clamp(value, minv, maxv):
            return max(minv, min(value, maxv))

        return 92 - (clamp(i, 0, 7) * 8) + clamp(j, 0, 7)

    def set_pad_color(self, i, j, color='white', animation='static'):
        """Sets the color of the pad at the (i, j) coordinate.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#261-setting-led-colors
        """
        pad = self.coords_to_pad_midi_number(i, j)
        color = RGB_COLORS.get(color, RGB_DEFAULT_COLOR)
        animation = ANIMATIONS.get(animation, ANIMATIONS_DEFAULT)
        msg = mido.Message('note_on', note=pad, velocity=color, channel=1)
        self.midi_out_port.send(msg)

    def set_pads_color(self, color_matrix, animation_matrix=None):
        """Sets the color and animations of all pads according to the given matrices.
        Matrices must be 8x8, with 8 lines of 8 values corresponding to the pad grid from top-left to bottom-down.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#261-setting-led-colors
        """
        assert len(color_matrix) == 8, 'Wrong number of lines in color matrix ({0})'.format(len(color_matrix))
        if animation_matrix is not None:
            assert len(animation_matrix) == 8, 'Wrong number of lines in animation matrix ({0})'.format(len(animation_matrix))
        for i, line in enumerate(color_matrix):
            assert len(line) == 8, 'Wrong number of color values in line ({0})'.format(len(line))
            if animation_matrix is not None:
                assert len(animation_matrix[i]) == 8, 'Wrong number of animation values in line ({0})'.format(len(animation_matrix[i]))
            for j, color in enumerate(line):
                animation = None
                if animation_matrix is not None:
                    animation = animation_matrix[i][j]
                self.set_pad_color(i, j, color=color, animation=animation)

    def set_all_pads_to_color(self, color='white', animation='static'):
        """Set all pads to the given color/animation.
        """
        color_matrix = [[color for _ in range(0, 8)] for _ in range(0, 8)]
        animation_matrix = [[animation for _ in range(0, 8)] for _ in range(0, 8)]
        self.set_pads_color(color_matrix, animation_matrix)
    
    def set_all_pads_to_white(self, animation='static'):
        self.set_all_pads_to_color('white', animation=animation)

    def set_all_pads_to_red(self, animation='static'):
        self.set_all_pads_to_color('red', animation=animation)

    def set_all_pads_to_green(self, animation='static'):
        self.set_all_pads_to_color('green', animation=animation)

    def set_all_pads_to_blue(self, animation='static'):
        self.set_all_pads_to_color('blue', animation=animation)
