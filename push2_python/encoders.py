import mido
from .constants import ANIMATION_DEFAULT, MIDO_CONTROLCHANGE, \
    MIDO_NOTEON, MIDO_NOTEOFF, ACTION_ENCODER_ROTATED, ACTION_ENCODER_TOUCHED, ACTION_ENCODER_RELEASED
from .classes import AbstractPush2Section


def get_individual_encoder_action_name(action_name, encoder_name):
        return '{0} - {1}'.format(action_name, encoder_name)


class Push2Encoders(AbstractPush2Section):
    """Class to interface with Ableton's Push2 encoders.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#Encoders
    """

    encoder_map = None
    encoder_touch_map = None
    encoder_names_index = None
    encoder_names_list = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.encoder_map = {
            data['Number']: data for data in self.push.push2_map['Parts']['RotaryEncoders']}
        self.encoder_touch_map = {
            data['Touch']['Number']: data for data in self.push.push2_map['Parts']['RotaryEncoders']}
        self.encoder_names_index = {data['Name']: data['Number']
                                    for data in self.push.push2_map['Parts']['RotaryEncoders']}
        self.encoder_names_list = list(self.encoder_names_index.keys())

    @property
    def available_names(self):
        return self.encoder_names_list

    def encoder_name_to_encoder_n(self, encoder_name):
        """
        Gets encoder number from given encoder name
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#23-midi-mapping
        """
        return self.encoder_names_index.get(encoder_name, None)

    def on_midi_message(self, message):
        if message.type == MIDO_CONTROLCHANGE:  # Encoder rotated
            if message.control in self.encoder_map:  # CC number corresponds to one of the encoders
                if message.type == MIDO_CONTROLCHANGE:
                    encoder = self.encoder_map[message.control]
                    action = ACTION_ENCODER_ROTATED
                    value = message.value
                    if message.value > 63:
                        # Counter-clockwise movement, see https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#Encoders
                        value = -1 * (128 - message.value)
                    self.push.trigger_action(action, encoder['Name'], value)  # Trigger generic rotate encoder action
                    self.push.trigger_action(get_individual_encoder_action_name(
                        action, encoder['Name']), value)  # Trigger individual rotate encoder action as well
                    return True
        elif message.type in [MIDO_NOTEON, MIDO_NOTEOFF]:  # Encoder touched or released
            if message.note in self.encoder_touch_map:  # Note number corresponds to one of the encoders in touch mode
                encoder = self.encoder_touch_map[message.note]
                action = ACTION_ENCODER_TOUCHED if message.velocity == 127 else ACTION_ENCODER_RELEASED
                self.push.trigger_action(action, encoder['Name'])  # Trigger generic touch/release encoder action
                self.push.trigger_action(get_individual_encoder_action_name(
                    action, encoder['Name']))  # Trigger individual touch/release encoder action as well
                return True
