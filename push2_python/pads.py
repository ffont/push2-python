import mido
from .constants import RGB_COLORS, RGB_DEFAULT_COLOR, ANIMATIONS, ANIMATIONS_DEFAULT, MIDO_NOTEON, MIDO_NOTEOFF, MIDO_POLYAT, ACTION_PAD_PRESSED, ACTION_PAD_RELEASED, ACTION_PAD_AFTERTOUCH
from .classes import AbstractPush2Section


def pad_ij_to_pad_n(i, j):
    """Transform (i, j) coordinates to the corresponding pad number
    according to the specification. (0, 0) corresponds to the top-left pad while
    (7, 7) corresponds to the bottom right pad.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#23-midi-mapping
    """

    def clamp(value, minv, maxv):
        return max(minv, min(value, maxv))

    return 92 - (clamp(i, 0, 7) * 8) + clamp(j, 0, 7)


def pad_n_to_pad_ij(n):
    """Transform MIDI note number to pad (i, j) coordinates.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#23-midi-mapping
    """
    return (99 - n) // 8, 7 - (99 - n) % 8


def get_individual_pad_action_name(action_name, pad_n=None, pad_ij=None):
    n = pad_n
    if pad_n is None:
        n = pad_ij_to_pad_n(pad_ij[0], pad_ij[1])
    return '{0} - {1}'.format(action_name, n)


class Push2Pads(AbstractPush2Section):
    """Class to interface with Ableton's Push2 pads.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#Pads
    """

    def set_polyphonic_aftertouch(self):
        """Set pad aftertouch mode to polyphonic aftertouch
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#285-aftertouch
        """
        msg = mido.Message.from_bytes([0xF0, 0x00, 0x21, 0x1D, 0x01, 0x01, 0x1E, 0x01, 0xF7])
        self.push.send_midi_to_push(msg)

    def set_channel_aftertouch(self):
        """Set pad aftertouch mode to channel aftertouch
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#285-aftertouch
        """
        msg = mido.Message.from_bytes([0xF0, 0x00, 0x21, 0x1D, 0x01, 0x01, 0x1E, 0x00, 0xF7])
        self.push.send_midi_to_push(msg)

    def pad_ij_to_pad_n(self, i, j):
        return pad_ij_to_pad_n(i, j)

    def pad_n_to_pad_ij(self, n):
        return pad_n_to_pad_ij(n)

    def set_pad_color(self, i, j, color='white', animation='static'):
        """Sets the color of the pad at the (i, j) coordinate.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#261-setting-led-colors
        """
        pad = self.pad_ij_to_pad_n(i, j)
        color = RGB_COLORS.get(color, RGB_DEFAULT_COLOR)
        animation = ANIMATIONS.get(animation, ANIMATIONS_DEFAULT)
        msg = mido.Message(MIDO_NOTEON, note=pad, velocity=color, channel=animation)
        self.push.send_midi_to_push(msg)

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

    def on_midi_message(self, message):
        if message.type in [MIDO_NOTEON, MIDO_NOTEOFF, MIDO_POLYAT]:
            if 36 <= message.note <= 99:  # Min and max pad MIDI values according to Push Spec
                pad_n = message.note
                pad_ij = self.pad_n_to_pad_ij(pad_n)
                if message.type == MIDO_POLYAT:
                    velocity = message.value
                else:
                    velocity = message.velocity
                if message.type == MIDO_NOTEON:   
                    self.push.trigger_action(ACTION_PAD_PRESSED, pad_n, pad_ij, velocity)  # Trigger generic pad action
                    self.push.trigger_action(get_individual_pad_action_name(
                        ACTION_PAD_PRESSED, pad_n=pad_n), velocity)  # Trigger individual pad action as well
                elif message.type == MIDO_NOTEOFF:
                    self.push.trigger_action(ACTION_PAD_RELEASED, pad_n, pad_ij, velocity)
                    self.push.trigger_action(get_individual_pad_action_name(
                        ACTION_PAD_RELEASED, pad_n=pad_n), velocity)  # Trigger individual pad action as well
                elif message.type == MIDO_POLYAT:
                    self.push.trigger_action(ACTION_PAD_AFTERTOUCH, pad_n, pad_ij, velocity)
                    self.push.trigger_action(get_individual_pad_action_name(
                        ACTION_PAD_AFTERTOUCH, pad_n=pad_n), velocity)  # Trigger individual pad action as well
