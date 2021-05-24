import mido
from .constants import ANIMATION_DEFAULT, MIDO_NOTEON, MIDO_NOTEOFF, \
    MIDO_POLYAT, MIDO_AFTERTOUCH, ACTION_PAD_PRESSED, ACTION_PAD_RELEASED, ACTION_PAD_AFTERTOUCH, PUSH2_SYSEX_PREFACE_BYTES, \
    PUSH2_SYSEX_END_BYTES, ANIMATION_STATIC
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

    current_pads_state = dict()

    def reset_current_pads_state(self):
        """This function resets the stored pads state to avoid Push2 pads becoming out of sync with the push2-midi stored state.
        This only applies if "optimize_num_messages" is used in "set_pad_color" as it would stop sending a message if the
        desired color is already the one listed in the internal state.
        """
        self.current_pads_state = dict()


    def set_polyphonic_aftertouch(self):
        """Set pad aftertouch mode to polyphonic aftertouch
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#285-aftertouch
        """
        msg = mido.Message.from_bytes(PUSH2_SYSEX_PREFACE_BYTES + [0x1E, 0x01] + PUSH2_SYSEX_END_BYTES)
        self.push.send_midi_to_push(msg)

    def set_channel_aftertouch(self):
        """Set pad aftertouch mode to channel aftertouch
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#285-aftertouch
        """
        msg = mido.Message.from_bytes(PUSH2_SYSEX_PREFACE_BYTES + [0x1E, 0x00] + PUSH2_SYSEX_END_BYTES)
        self.push.send_midi_to_push(msg)


    def set_channel_aftertouch_range(self, range_start=401, range_end=2048):
        """Configures the sensitivity of channel aftertouch by defining at what "range start" pressure value the aftertouch messages
        start to be triggered and what "range end" pressure value corresponds to the aftertouch value 127. I'm not sure about the meaning
        of the pressure values, but according to the documentation must be between 400 and 2048.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#282-pad-parameters
        """
        assert type(range_start) == int and type(range_end) == int, "range_start and range_end must be int"
        assert range_start < range_end, "range_start must be lower than range_end"
        assert 400 < range_start < range_end, "wrong range_start value, must be in range [401, range_end]"
        assert range_start < range_end <= 2048, "wrong range_end value, must be in range [range_start + 1, 2048]"
        lower_range_bytes = [range_start % 2**7, range_start // 2**7]
        upper_range_bytes = [range_end % 2**7, range_end // 2**7]
        msg = mido.Message.from_bytes(PUSH2_SYSEX_PREFACE_BYTES + [0x1B, 0x00, 0x00, 0x00, 0x00] + lower_range_bytes + upper_range_bytes + PUSH2_SYSEX_END_BYTES)
        self.push.send_midi_to_push(msg)


    def set_velocity_curve(self, velocities):
        """Configures Push pad's velocity curve which will determine i) the velocity values triggered when pressing pads; and ii) the
        sensitivity of the aftertouch when in polyphonic aftertouch mode. Push uses a map of physical pressure values [0g..4095g]
        to MIDI velocity values [0..127]. This map is quantized into 128 steps which Push then interpolates. This method expects a list of 
        128 velocity values which will be assigned to each of the 128 quantized steps of the physical pressure range [0g..4095g].
        See hhttps://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#281-velocity-curve
        """
        assert type(velocities) == list and len(velocities) == 128 and type(velocities[0] == int), "velocities must be a list with 128 int values"
        for start_index in range(0, 128, 16):
            msg = mido.Message.from_bytes(PUSH2_SYSEX_PREFACE_BYTES + [0x20] + [start_index] + velocities[start_index:start_index + 16] + PUSH2_SYSEX_END_BYTES)
            self.push.send_midi_to_push(msg)

    def pad_ij_to_pad_n(self, i, j):
        return pad_ij_to_pad_n(i, j)

    def pad_n_to_pad_ij(self, n):
        return pad_n_to_pad_ij(n)

    def set_pad_color(self, pad_ij, color='white', animation=ANIMATION_DEFAULT, optimize_num_messages=True, animation_end_color='black'):
        """Sets the color of the pad at the (i,j) coordinate.
        'color' must be a valid RGB color name present in the color palette. See push2_python.constants.DEFAULT_COLOR_PALETTE for default color names.
        'animation' must be a valid animation name from those defined in push2_python.contants.ANIMATION_*. Note that to configure an animation, both 
        the 'start' and 'end' colors of the animation need to be defined. The 'start' color is defined by 'color' parameter. The 'end' color is defined 
        by the color specified in 'animation_end_color', which must be a valid RGB color name present in the color palette.
        
        This funtion will keep track of the latest color/animation values set for each specific pad. If 'optimize_num_messages' is 
        set to True, set_pad_color will only actually send the MIDI message to push if either the color or animation that should 
        be set differ from those stored in the state.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#261-setting-led-colors
        """
        pad = self.pad_ij_to_pad_n(pad_ij[0], pad_ij[1])
        color = self.push.get_rgb_color(color)
        if optimize_num_messages and pad in self.current_pads_state and self.current_pads_state[pad]['color'] == color and self.current_pads_state[pad]['animation'] == animation:
            # If pad's recorded state already has the specified color and animation, return method before sending the MIDI message
            return
        if animation != ANIMATION_STATIC:
            # If animation is not static, we first set the pad to black color with static animation so then, when setting
            # the desired color with the corresponding animation it lights as expected.
            msg = mido.Message(MIDO_NOTEON, note=pad, velocity=self.push.get_rgb_color(animation_end_color), channel=ANIMATION_STATIC)
            self.push.send_midi_to_push(msg)
        msg = mido.Message(MIDO_NOTEON, note=pad, velocity=color, channel=animation)
        self.push.send_midi_to_push(msg)
        self.current_pads_state[pad] = {'color': color, 'animation': animation}

        if self.push.simulator_controller is not None:
            self.push.simulator_controller.set_element_color('nn' + str(pad), color, animation)

    def set_pads_color(self, color_matrix, animation_matrix=None):
        """Sets the color and animations of all pads according to the given matrices.
        Individual elements in the color_matrix must be valid RGB color palette names. See push2_python.constants.DEFAULT_COLOR_PALETTE for default color names.
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
                animation = ANIMATION_DEFAULT
                animation_end_color = 'black'
                if animation_matrix is not None:
                    element = animation_matrix[i][j]
                    if type(element) == tuple:
                        animation, animation_end_color = animation_matrix[i][j]
                    else:
                        animation = animation_matrix[i][j]
                self.set_pad_color((i, j), color=color, animation=animation, animation_end_color=animation_end_color)

    def set_all_pads_to_color(self, color='white', animation=ANIMATION_DEFAULT, animation_end_color='black'):
        """Set all pads to the given color/animation.
        'color' must be a valid RGB color name present in the color palette. See push2_python.constants.DEFAULT_COLOR_PALETTE for default color names.
        'animation' must be a valid animation name from those defined in push2_python.contants.ANIMATION_*. Note that to configure an animation, both the 'start' and 'end'
        colors of the animation need to be defined. The 'start' color is defined by setting a color with 'push2_python.contants.ANIMATION_STATIC' (the default).
        The second color is set setting a color with whatever ANIMATION_* type is desired.
        """
        color_matrix = [[color for _ in range(0, 8)] for _ in range(0, 8)]
        animation_matrix = [[(animation, animation_end_color) for _ in range(0, 8)] for _ in range(0, 8)]
        self.set_pads_color(color_matrix, animation_matrix)

    def set_all_pads_to_black(self, animation=ANIMATION_DEFAULT, animation_end_color='black'):
        self.set_all_pads_to_color('black', animation=animation, animation_end_color=animation_end_color)
    
    def set_all_pads_to_white(self, animation=ANIMATION_DEFAULT, animation_end_color='black'):
        self.set_all_pads_to_color('white', animation=animation, animation_end_color=animation_end_color)

    def set_all_pads_to_red(self, animation=ANIMATION_DEFAULT, animation_end_color='black'):
        self.set_all_pads_to_color('red', animation=animation, animation_end_color=animation_end_color)

    def set_all_pads_to_green(self, animation=ANIMATION_DEFAULT, animation_end_color='black'):
        self.set_all_pads_to_color('green', animation=animation, animation_end_color=animation_end_color)

    def set_all_pads_to_blue(self, animation=ANIMATION_DEFAULT, animation_end_color='black'):
        self.set_all_pads_to_color('blue', animation=animation, animation_end_color=animation_end_color)

    def on_midi_message(self, message):
        if message.type in [MIDO_NOTEON, MIDO_NOTEOFF, MIDO_POLYAT, MIDO_AFTERTOUCH]:
            if message.type != MIDO_AFTERTOUCH:
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
                        return True
                    elif message.type == MIDO_NOTEOFF:
                        self.push.trigger_action(ACTION_PAD_RELEASED, pad_n, pad_ij, velocity)
                        self.push.trigger_action(get_individual_pad_action_name(
                            ACTION_PAD_RELEASED, pad_n=pad_n), velocity)  # Trigger individual pad action as well
                        return True
                    elif message.type == MIDO_POLYAT:
                        self.push.trigger_action(ACTION_PAD_AFTERTOUCH, pad_n, pad_ij, velocity)
                        self.push.trigger_action(get_individual_pad_action_name(
                            ACTION_PAD_AFTERTOUCH, pad_n=pad_n), velocity)  # Trigger individual pad action as well
                        return True
            elif message.type == MIDO_AFTERTOUCH:
                self.push.trigger_action(ACTION_PAD_AFTERTOUCH, None, None, message.value)
                return True
