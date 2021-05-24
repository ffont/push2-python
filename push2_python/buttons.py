import mido
from .constants import ANIMATION_DEFAULT, MIDO_CONTROLCHANGE, ACTION_BUTTON_PRESSED, ACTION_BUTTON_RELEASED, ANIMATION_STATIC
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

    def set_button_color(self, button_name, color='white', animation=ANIMATION_DEFAULT, animation_end_color='black'):
        """Sets the color of the button with given name.
        'color' must be a valid RGB or BW color name present in the color palette. See push2_python.constants.DEFAULT_COLOR_PALETTE for default color names.
        If the button only acceps BW colors, the color name will be matched against the BW palette, otherwise it will be matched against RGB palette.
        'animation' must be a valid animation name from those defined in push2_python.contants.ANIMATION_*.  Note that to configure an animation, both 
        the 'start' and 'end' colors of the animation need to be defined. The 'start' color is defined by 'color' parameter. The 'end' color is defined 
        by the color specified in 'animation_end_color', which must be a valid RGB color name present in the color palette.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#setting-led-colors
        """
        button_n = self.button_name_to_button_n(button_name)
        if button_n is not None:
            button = self.button_map[button_n]
            if button['Color']:
                color_idx = self.push.get_rgb_color(color)
                black_color_idx = self.push.get_rgb_color(animation_end_color)
            else:
                color_idx = self.push.get_bw_color(color)
                black_color_idx = self.push.get_bw_color(animation_end_color)
            if animation != ANIMATION_STATIC:
                # If animation is not static, we first set the button to black color with static animation so then, when setting
                # the desired color with the corresponding animation it lights as expected.
                # This behaviour should be furhter investigated as this could maybe be optimized.
                msg = mido.Message(MIDO_CONTROLCHANGE, control=button_n, value=black_color_idx, channel=ANIMATION_STATIC)
                self.push.send_midi_to_push(msg)
            msg = mido.Message(MIDO_CONTROLCHANGE, control=button_n, value=color_idx, channel=animation)
            self.push.send_midi_to_push(msg)

            if self.push.simulator_controller is not None:
                self.push.simulator_controller.set_element_color('cc' + str(button_n), color_idx, animation)

    def set_all_buttons_color(self, color='white', animation=ANIMATION_DEFAULT, animation_end_color='black'):
        """Sets the color of all buttons in Push2 to the given color.
        'color' must be a valid RGB or BW color name present in the color palette. See push2_python.constants.DEFAULT_COLOR_PALETTE for default color names.
        If the button only acceps BW colors, the color name will be matched against the BW palette, otherwise it will be matched against RGB palette.
        'animation' must be a valid animation name from those defined in push2_python.contants.ANIMATION_*. Note that to configure an animation, both 
        the 'start' and 'end' colors of the animation need to be defined. The 'start' color is defined by 'color' parameter. The 'end' color is defined 
        by the color specified in 'animation_end_color', which must be a valid RGB color name present in the color palette.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#setting-led-colors
        """
        for button_name in self.available_names:
            self.set_button_color(button_name, color=color, animation=animation, animation_end_color=animation_end_color)
        
    def on_midi_message(self, message):
        if message.type == MIDO_CONTROLCHANGE:
            if message.control in self.button_map:  # CC number corresponds to one of the buttons
                button = self.button_map[message.control]
                action = ACTION_BUTTON_PRESSED if message.value == 127 else ACTION_BUTTON_RELEASED
                self.push.trigger_action(action, button['Name'])  # Trigger generic button action
                self.push.trigger_action(get_individual_button_action_name(action, button['Name']))  # Trigger individual button action as well
                return True

