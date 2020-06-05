import mido
from .constants import ANIMATIONS, ANIMATIONS_DEFAULT, MIDO_CONTROLCHANGE, ACTION_BUTTON_PRESSED, ACTION_BUTTON_RELEASED
from .classes import AbstractPush2Section


def get_individual_button_action_name(action_name, button_name):
        return '{0} - {1}'.format(action_name, button_name)


class Push2Buttons(AbstractPush2Section):
    """Class to interface with Ableton's Push2 buttons.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#Buttons
    """

    button_map = None
    button_names_index = None
    button_names_list = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button_map = {data['Number']: data for data in self.push.push2_map['Parts']['Buttons']}
        self.button_names_index = {data['Name']: data['Number'] for data in self.push.push2_map['Parts']['Buttons']}
        self.button_names_list = list(self.button_names_index.keys())

    @property
    def available_names(self):
        return self.button_names_list

    def button_name_to_button_n(self, button_name):
        """
        Gets button number from given button name
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#23-midi-mapping
        """
        return self.button_names_index.get(button_name, None)

    def set_button_color(self, button_name, color='white', animation='static'):
        """Sets the color of the button with given name.
        'color' must be a valid RGB or BW color name present in the color palette. See push2_python.constants.DEFAULT_COLOR_PALETTE for default color names.
        If the button only acceps BW colors, the color name will be matched against the BW palette, otherwise it will be matched against RGB palette.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#setting-led-colors
        """
        button_n = self.button_name_to_button_n(button_name)
        if button_n is not None:
            button = self.button_map[button_n]
            if button['Color']:
                color_idx = self.push.get_rgb_color(color)
            else:
                color_idx = self.push.get_bw_color(color)
            animation = ANIMATIONS.get(animation, ANIMATIONS_DEFAULT)
            msg = mido.Message(MIDO_CONTROLCHANGE, control=button_n, value=color_idx, channel=animation)
            self.push.send_midi_to_push(msg)
        
    def on_midi_message(self, message):
        if message.type == MIDO_CONTROLCHANGE:
            if message.control in self.button_map:  # CC number corresponds to one of the buttons
                button = self.button_map[message.control]
                action = ACTION_BUTTON_PRESSED if message.value == 127 else ACTION_BUTTON_RELEASED
                self.push.trigger_action(action, button['Name'])  # Trigger generic button action
                self.push.trigger_action(get_individual_button_action_name(action, button['Name']))  # Trigger individual button action as well

