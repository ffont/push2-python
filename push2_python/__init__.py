import usb.core
import usb.util
import logging
import sys
import mido
import threading
import time
from datetime import timedelta
from collections import defaultdict
from .classes import function_call_interval_limit
from .exceptions import Push2USBDeviceNotFound, Push2USBDeviceConfigurationError, Push2MIDIeviceNotFound
from .display import Push2Display
from .pads import Push2Pads, get_individual_pad_action_name
from .buttons import Push2Buttons, get_individual_button_action_name
from .encoders import Push2Encoders, get_individual_encoder_action_name
from .touchstrip import Push2TouchStrip
from .push2_map import push2_map
from .constants import is_push_midi_in_port_name, is_push_midi_out_port_name, PUSH2_MAP_FILE_PATH, ACTION_BUTTON_PRESSED, \
    ACTION_BUTTON_RELEASED, ACTION_TOUCHSTRIP_TOUCHED, ACTION_PAD_PRESSED, ACTION_PAD_RELEASED, ACTION_PAD_AFTERTOUCH, \
    ACTION_ENCODER_ROTATED, ACTION_ENCODER_TOUCHED, ACTION_ENCODER_RELEASED, PUSH2_RECONNECT_INTERVAL, ACTION_DISPLAY_CONNECTED, \
    ACTION_DISPLAY_DISCONNECTED, ACTION_MIDI_CONNECTED, ACTION_MIDI_DISCONNECTED, PUSH2_MIDI_ACTIVE_SENSING_MAX_INTERVAL, ACTION_SUSTAIN_PEDAL, \
    MIDO_CONTROLCHANGE, PUSH2_SYSEX_PREFACE_BYTES, PUSH2_SYSEX_END_BYTES, DEFAULT_COLOR_PALETTE, DEFAULT_RGB_COLOR, DEFAULT_BW_COLOR

from .simulator.simulator import start_simulator

logging.basicConfig(stream=sys.stdout, level=logging.ERROR)

action_handler_registry = defaultdict(list)


class Push2(object):
    """Class to interface with Ableton's Push2.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc
    """
    midi_in_port = None
    midi_out_port = None
    push2_map = None
    display = None
    pads = None
    buttons = None
    encoders = None
    touchstrip = None
    use_user_midi_port = False
    last_active_sensing_received = None
    function_call_interval_limit_overwrite = PUSH2_RECONNECT_INTERVAL
    color_palette = DEFAULT_COLOR_PALETTE.copy()
    simulator_controller = None


    def __init__(self, use_user_midi_port=False, run_simulator=False, simulator_port=6128, simulator_use_virtual_midi_out=False):
        """Initializes object to interface with Ableton's Push2.
        This function will set up USB and MIDI connections with the hardware device.
        By default, MIDI connection will use LIVE MIDI port instead of USER MIDI port.
        USER MIDI port can be configured using the argument 'use_user_midi_port'. Alternatively
        a custom specific MIDI port name for Push can be provided using the argument 'push_midi_port_name'.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc
        """

        self.use_user_midi_port = use_user_midi_port

        # Load Push2 map from JSON file provided in Push2's interface doc
        # https://github.com/Ableton/push-interface/blob/master/doc/Push2-map.json
        self.push2_map = push2_map
        
        # Init individual sections
        self.display = Push2Display(self)
        self.pads = Push2Pads(self)
        self.buttons = Push2Buttons(self)
        self.encoders = Push2Encoders(self)
        self.touchstrip = Push2TouchStrip(self)

        # Initialize MIDI IN connection with push
        self.configure_midi(skip_midi_out=True)
        
        # NOTE: no need to initialize MIDI out connection and connection with display because
        # these will be lazily initialized when required (i.e., when attempting to send MIDI to push
        # or attempting to use the display)

        # Start thread that will continuously check whether the last "active sensing" MIDI message from
        # push was received. If active sensing messages stop, will set midi ports to None and trigger
        # a "midi disconnected" action
        def check_active_sensing(f_stop):
            if self.last_active_sensing_received is not None:
                if time.time() - self.last_active_sensing_received > PUSH2_MIDI_ACTIVE_SENSING_MAX_INTERVAL:
                    '''
                    # Don't set midi port connections to None because if these were ever initialized, will remain
                    # active once Push2 MIDI comes back (e.g. after Push2 reset) and we will start receiving again
                    # active sensing messages (and will be able to re-trigger "push midi connected" message without
                    # actively continuously checking for MIDI connection using some sort of polling strategy.
                    if self.midi_is_configured():
                        if self.midi_in_port is not None:
                            self.midi_in_port.close()
                            self.midi_in_port = None
                        if self.midi_out_port is not None:
                            self.midi_out_port.close()
                            self.midi_out_port = None
                    '''
                    self.trigger_action(ACTION_MIDI_DISCONNECTED)
                    self.last_active_sensing_received = None
            if not f_stop.is_set():
                threading.Timer(0.3, check_active_sensing, [f_stop]).start()  # Run this check every 300 ms

        self.f_stop = threading.Event()
        check_active_sensing(self.f_stop)

        # Initialize simulator (if requested)
        if run_simulator:
            self.simulator_controller = start_simulator(self, port=simulator_port, use_virtual_midi_out=simulator_use_virtual_midi_out)


    def stop_active_sensing_thread(self):
        self.f_stop.set()


    def set_push2_reconnect_call_interval(self, new_interval):
        self.function_call_interval_limit_overwrite = new_interval
        self.display.function_call_interval_limit_overwrite = new_interval


    def trigger_action(self, *args, **kwargs):
        action_name = args[0]
        new_args = [self]
        if len(args) > 1:
            new_args += list(args[1:])
        for action, func in action_handler_registry.items():
            if action == action_name:
                func[0](*new_args, **kwargs)  # TODO: why is func a 1-element list?


    @function_call_interval_limit(PUSH2_RECONNECT_INTERVAL)
    def configure_midi(self, skip_midi_out=False, skip_midi_in=False):
        """Calling this function will try to configure MIDI in/out connection with Push2. If configuration
        is already properly set up, nothing will be done so it is safe to call this even if MIDI has already
        been configured. 
        
        This function is decorated with 'function_call_interval_limit' which means that it is only going to be executed 
        if PUSH2_RECONNECT_INTERVAL seconds have passed since the last time the function was called. This is to avoid 
        potential problems trying to configure MIDI many times per second. To ignore this limitation, 'self.configure_midi_out()' 
        and 'self.configure_midi_in()' can be called instead.
        """
        if not skip_midi_out:
            try:
                self.configure_midi_out()
            except (Push2MIDIeviceNotFound, ) as e:
                log_error = False
                if self.simulator_controller is not None:
                    if not hasattr(self, 'midi_out_init_error_shown'):
                        log_error = True
                        self.midi_out_init_error_shown = True
                else:
                    log_error = True
                if log_error:
                    logging.error('Could not initialize Push 2 MIDI out: {0}'.format(e))
        
        if not skip_midi_in:
            try:
                self.configure_midi_in()
            except (Push2MIDIeviceNotFound, ) as e:
                log_error = False
                if self.simulator_controller is not None:
                    if not hasattr(self, 'midi_in_init_error_shown'):
                        log_error = True
                        self.midi_in_init_error_shown = True
                else:
                    log_error = True
                if log_error:
                    logging.error('Could not initialize Push 2 MIDI in: {0}'.format(e))


    def configure_midi_in(self):
        if self.midi_in_port is None:
            port_name_to_use = None
            for port_name in mido.get_input_names():
                if is_push_midi_in_port_name(port_name, use_user_port=self.use_user_midi_port):
                    port_name_to_use = port_name
                    break

            if port_name_to_use is None:
                raise Push2MIDIeviceNotFound
                
            try:
                self.midi_in_port = mido.open_input(port_name_to_use)
                # Disable Active Sense message filtering so we can receive those messages comming from Push and
                # detect if Push MIDI gets disconnected
                self.midi_in_port._rt.ignore_types(False, False, False)
                self.midi_in_port.callback = self.on_midi_message
            except OSError as e:
                raise Push2MIDIeviceNotFound


    def configure_midi_out(self):
        if self.midi_out_port is None:
            port_name_to_use = None
            for port_name in mido.get_output_names():
                if is_push_midi_out_port_name(port_name, use_user_port=self.use_user_midi_port):
                    port_name_to_use = port_name
                    break
                    
            if port_name_to_use is None:
                raise Push2MIDIeviceNotFound
            
            try:
                self.midi_out_port = mido.open_output(port_name_to_use)
            except OSError as e:
                raise Push2MIDIeviceNotFound


    def midi_is_configured(self):
        """Returns True if MIDI communication with Push2 is properly configured, False otherwise
        """
        return self.midi_in_port is not None and self.midi_out_port is not None


    def send_midi_to_push(self, msg):

        # If MIDI is not configured, configure it now
        if not self.midi_is_configured():
            self.configure_midi()

        # If MIDI out was properly configured, send the MIDI message
        if self.midi_out_port is not None:
            self.midi_out_port.send(msg)


    def on_midi_message(self, message):
        """Handle incomming MIDI messages from Push.
        Call `on_midi_nessage` for each individual section.
        """
        current_time = time.time()
        if (message.type == "active_sensing"):
            active_sensing_was_none = self.last_active_sensing_received is None
            self.last_active_sensing_received = current_time
            if active_sensing_was_none:
                # Means this is first active_sensing received message (possibly after Push2 restart) and therefore initial MIDI setup (if any) should be done
                self.pads.reset_current_pads_state()  # Reset stored pads state (if any) to avoid messages not being sent because of state
                self.trigger_action(ACTION_MIDI_CONNECTED)
                self.last_action_midi_connection_action_triggered = current_time
        else:
            if self.last_active_sensing_received is not None and current_time - self.last_action_midi_connection_action_triggered > 1:
                # Right after first "active sensing" message is received (which means MIDI IN conneciton with Push is properly set),
                # ignore the next 1 second of MIDI in messages as for some reason these include a burst of messages from Push which we 
                # are not interested in (probably some internal state which Ableton uses but we don't care about?)
                
                # Send received message to each "part" so it is processes accordingly
                for func in [self.pads.on_midi_message, self.buttons.on_midi_message, self.encoders.on_midi_message, self.touchstrip.on_midi_message]:
                    action_taken = func(message)
                    if action_taken:
                        break  # Early return from for loop to avoid running unnecessary checks

                # Also check for some other extra general message types here
                if message.type == MIDO_CONTROLCHANGE:
                    if message.control == 64:  # Sustain pedal
                        self.trigger_action(ACTION_SUSTAIN_PEDAL, message.value >= 64)

        logging.debug('Received MIDI message from Push: {0}'.format(message))


    def set_color_palette_entry(self, color_idx, color_name, rgb=None, bw=None, allow_overwrite=False):
        """Updates internal Push color palette so that colors for pads and buttons can be customized.
        Using this method will update the color palette in Push hardware, and also the color palette used by the Push2 python object
        so that colors can be changed accordingly.

        The way color palette is updated is by specifying a color index ('color_idx' parameter, range [0..127]) and its corresponding rgb values ('rgb'
        parameter, as a 3-element list of floats from [0..1] or integers [0..255]) and/or black and white value ('bw' parameter, as a single
        brilliance float from [0..1] or integer [0..255]). Therefore, this method allows you to specify a color for the same color entry in
        the RGB and BW palettes. If either 'rgb' or 'bw' is not specified, this method will make an "intelligent" guess to set the other. In
        addition to 'color_idx' and 'rgb'/'bw' values, a 'color_name' must be given to further identify the color. 'color_name' should be
        either a str (in this case the same name will be used for the RGB and BW palettes), or as a 2-element list with the color corresponding
        to the 'rgb' color (1st element) and then name for the 'bw' color (2nd element).

        If 'allow_overwrite' is not set to True, this method will raise exception if the given color name already exists in the RGB or BW color
        palette.

        Note that changes in the Push color palete using this method won't become active until method 'reapply_color_palette' is called.

        Examples:

            # Configure palette entry 0 to be red (for rgb colors) and gray (for bw colors)
            set_color_palette_entry(0, ['red', 'gray'], rgb=[255, 0, 0], bw=128)  

            # Configure palette entry 0 to be dark green (for rgb colors) and white (for bw colors)
            set_color_palette_entry(0, ['dark green', 'white'], rgb=[0, 100, 0], bw=255)  

            # Apply the changes in Push
            reapply_color_palette()
            

        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#262-rgb-led-color-processing
        """

        assert type(color_idx) == int, 'Parameter "color_idx" must be an integer'
        assert 0 <= color_idx <= 127, 'Parameter "color_idx" must be in range [0..127]'

        assert rgb is not None or bw is not None, 'At least "rgb" or "bw" parameter (or both) should be provided'
        
        if rgb is not None:
            assert len(rgb) == 3, 'Parameter "rgb" should have 3 elements'

        if type(color_name) == str:
            color_names = [color_name, color_name]
        else:
            assert len(color_name) == 2, 'Parameter "color_name" should have 2 elements'
            color_names = color_name

        if not allow_overwrite:
            assert color_names[0] not in [rgb_color_name for rgb_color_name, _ in self.color_palette.values()], 'A color with name "{0}" for RGB palette already exists'.format(color_names[0])
            assert color_names[1] not in [bw_color_name for _, bw_color_name in self.color_palette.values()], 'A color with name "{0}" for BW palette already exists'.format(color_names[1])

        def check_color_range(c):
            # If color is float, map it to [0..255], also check range is inside [0..255]
            if type(c) == float:
                c = int(round(c * 255))
            if c < 0:
                c = 0
            elif c > 255:
                c = 255
            return c

        if rgb is not None:
            r = check_color_range(rgb[0])
            g = check_color_range(rgb[1])
            b = check_color_range(rgb[2])
        else:
            # If rgb is not provided, w will have been provided, use this number for all components
            r = check_color_range(bw)
            g = r
            b = r

        if bw is not None:
            w = check_color_range(bw)
        else:
            # If white is not provided, rgb will have been provided, use an average of it ti decide white
            w = check_color_range(int((r + g + b) / 3))

        # Send message to Push to update internal color palette
        red_bytes = [r % 128, r // 128]
        green_bytes = [g % 128, g // 128]
        blue_bytes = [b % 128, b // 128]
        white_bytes = [w % 128, w // 128]
        message_bytes = PUSH2_SYSEX_PREFACE_BYTES + [0x03] + [color_idx] + red_bytes + green_bytes + blue_bytes + white_bytes + PUSH2_SYSEX_END_BYTES
        msg = mido.Message.from_bytes(message_bytes)
        self.send_midi_to_push(msg)

        # Update self.color_palette with given color names (first one for rgb, second one for bw)
        self.color_palette[color_idx] = color_names

        # Update color in simulator (if it is being run...)
        if self.simulator_controller is not None:
            self.simulator_controller.update_color_palette_entry(color_idx, (r, g, b), (w, w, w))


    def update_rgb_color_palette_entry(self, color_name, rgb):
        """This method finds an RGB color name in the RGB palette and updates it's color values to the given rgb.
        See 'set_color_palette_entry' for details on how rgb values should be given.
        Note that if ther's a BW color in the same RGB color name entry, it will be overwriten.
        Note that changes in the Push color palete using this method won't become active until method 'reapply_color_palette' is called.

        Example:
        
            # Customize 'green' colour
            update_rgb_color_palette_entry('green', [0, 0, 240])
            
            # Apply the changes in Push
            reapply_color_palette()
        """
        idx = None
        for color_idx, (rgb_color_name, _) in self.color_palette.items():
            if color_name == rgb_color_name:
                idx = color_idx
        assert idx is not None, 'No color with name {0} is in RGB color palette'.format(color_name)
        self.set_color_palette_entry(idx, color_name, rgb=rgb, allow_overwrite=True)


    def get_rgb_color(self, color_name):
        """Get correpsonding color index of the color palette for a RGB color name.
        If color is not found, the default RGB index value will be returned.
        """
        for color_idx, (rgb_color_name, _) in self.color_palette.items():
            if color_name == rgb_color_name:
                return color_idx
        return DEFAULT_RGB_COLOR


    def get_bw_color(self, color_name):
        """Get correpsonding color index of the color palette for a BW color name.
        If color is not found, the default BW index value will be returned.
        """
        for color_idx, (_, bw_color_name) in self.color_palette.items():
            if color_name == bw_color_name:
                return color_idx
        return DEFAULT_BW_COLOR

    def reapply_color_palette(self):
        """This method sends a sysex message to Push to make it update the colors of all pads and buttons according to the color palette entries
        that have been updated using the 'set_color_palette_entry' method.
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#262-rgb-led-color-processing
        """
        message_bytes =  PUSH2_SYSEX_PREFACE_BYTES + [0x05] + PUSH2_SYSEX_END_BYTES
        msg = mido.Message.from_bytes(message_bytes)
        self.send_midi_to_push(msg)

    def display_is_configured(self):
        """Returns True if communication with Push2 display is properly configured, False otherwise
        """
        return self.display is not None and self.display.usb_endpoint is not None


def action_handler(action_name, button_name=None, pad_n=None, pad_ij=None, encoder_name=None):
    """
    Generic action handler decorator used by other specific decorators.
    This decorator should not be used directly. Specific decorators for individual actions should be used instead.
    """
    def wrapper(func):
        action = action_name
        if action_name in [ACTION_BUTTON_PRESSED, ACTION_BUTTON_RELEASED] and button_name is not None:
            # If the action is pressing or releasing a button and a spcific button name is given,
            # include the button name in the action name so that it can be triggered individually
            action = get_individual_button_action_name(action_name, button_name)
        if action_name in [ACTION_PAD_PRESSED, ACTION_PAD_RELEASED, ACTION_PAD_AFTERTOUCH] and (pad_n is not None or pad_ij is not None):
            # If the action is pressing, releasing or aftertouching a pad and a spcific pad number or
            # pad ij coordinates are given name was given, include the pad name or cordinate in the
            # action name so that it can be triggered individually
            action = get_individual_pad_action_name(action_name, pad_n=pad_n, pad_ij=pad_ij)
        if action_name in [ACTION_ENCODER_ROTATED, ACTION_ENCODER_TOUCHED, ACTION_ENCODER_RELEASED] and encoder_name is not None:
            # If the action is rotating, touching or releasing a rotatory encoder and a specific encoder
            # name is given, include the encoder name in the action name so that it can be triggered individually
            action = get_individual_encoder_action_name(action_name, encoder_name=encoder_name)
        logging.debug('Registered handler {0} for action {1}'.format(func, action))
        action_handler_registry[action].append(func)
        return func
    return wrapper


def on_button_pressed(button_name=None):
    """Shortcut for registering handlers for ACTION_BUTTON_PRESSED events.
    Optional "button_name" argument is to link the handler to a specific button.
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Button name (string, only if button name not specified in decorator)

    Examples:

    @push2_python.on_button_pressed()
    def function(push, button_name):
        print('Button', button_name, 'pressed')

    @push2_python.on_button_pressed(push2_python.constants.BUTTON_1_16)
    def function(push):
        print('Button 1/16 pressed')
    """
    return action_handler(ACTION_BUTTON_PRESSED, button_name=button_name)


def on_button_released(button_name=None):
    """Shortcut for registering handlers for ACTION_BUTTON_RELEASED events.
    Optional "button_name" argument is to link the handler to a specific button.
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Button name (string, only if button name not specified in decorator)

   Examples:

    @push2_python.on_button_released()
    def function(push, button_name):
        print('Button', button_name, 'released')

    @push2_python.on_button_released(push2_python.constants.BUTTON_1_16)
    def function(push):
        print('Button 1/6 released')
    """
    return action_handler(ACTION_BUTTON_RELEASED, button_name=button_name)


def on_touchstrip():
    """Shortcut for registering handlers for ACTION_TOUCHSTRIP_TOUCHED events. Push2's 
    touchstrip can be configured to work eithher as a pitch bend "wheel" (the default)
    or as a modualtion "wheel". When configured as pitch bend, the touchstrip values received
    in this method (see below) will correspond to pitch bend values [-8192, 8128]. If configured as
    modulation wheel, this function will receive the value of the modulation [0, 127]. Both
    modes can be configured by calling "set_modulation_wheel_mode" or "set_pitch_bend_mode" methods
    in Push2.touchstrip.
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Touchstrip value (int)

    Examples:

    @push2_python.on_touchstrip()
    def function(push, value):
        print('Touchstrip touched with value', value)
    """
    return action_handler(ACTION_TOUCHSTRIP_TOUCHED)


def on_pad_pressed(pad_n=None, pad_ij=None):
    """Shortcut for registering handlers for ACTION_PAD_PRESSED events.
    Optional "pad_n" or "pad_ij" arguments are to link the handler to a specific pad.
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Pad number (int, only if pad not specified in decorator)
        * Pad ij coordinates (tuple, only if pad not specified in decorator)
        * Velocity value (int 0-127)

    Examples:

    @push2_python.on_pad_pressed()
    def function(push, pad_n, pad_ij, velocity):
        print('Pad', pad_n, 'pressed with velocity', velocity)

    @push2_python.on_pad_pressed(pad_n=36)
    def function(push, velocity):
        print('Pad 36 pressed with velocity', velocity)

    @push2_python.on_pad_pressed(pad_ij=(0,3))
    def function(push, velocity):
        print('Pad (0, 3) pressed with velocity', velocity)
    """
    return action_handler(ACTION_PAD_PRESSED, pad_n=pad_n, pad_ij=pad_ij)


def on_pad_released(pad_n=None, pad_ij=None):
    """Shortcut for registering handlers for ACTION_PAD_RELEASED events.
    Optional "pad_n" or "pad_ij" arguments are to link the handler to a specific pad.
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Pad number (int, only if pad not specified in decorator)
        * Pad ij coordinates (tuple, only if pad not specified in decorator)
        * Release velocity value (int 0-127)

    Examples:

    @push2_python.on_pad_released()
    def function(push, pad_n, pad_ij, velocity):
        print('Pad', pad_n, 'released with velocity', velocity)

    @push2_python.on_pad_released(pad_n=36)
    def function(push, velocity):
        print('Pad 36 released with velocity', velocity)

    @push2_python.on_pad_released(pad_ij=(0,3))
    def function(push, velocity):
        print('Pad (0, 3) released with velocity', velocity)
    """
    return action_handler(ACTION_PAD_RELEASED, pad_n=pad_n, pad_ij=pad_ij)


def on_pad_aftertouch(pad_n=None, pad_ij=None):
    """Shortcut for registering handlers for ACTION_PAD_AFTERTOUCH events. This can
    work in "channel aftertouch" (cAT) or "polyphonic aftertouch" (polyAT) modes, which
    are configured using "set_polyphonic_aftertouch" or "set_channel_aftertouch" methods
    in Push2.pads. cAT mode is enabled by default. In polyAT mode Push will send individual
    aftertouch data for each pad, while in cAT mode aftertouch value will be shared for
    all pads. In polyAT mode, optional "pad_n" or "pad_ij" arguments can be passed to the
    decorator to link the handler to a specific pad adftertouch action.
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Pad number (int, only if pad not specified in decorator, will be none in cAT mode)
        * Pad ij position (tuple, only if pad not specified in decorator, will be none in cAT mode)
        * Aftertouch value (int 0-127)

    Examples:

    @push2_python.on_pad_aftertouch()
    def function(push, pad_n, pad_ij, value):
        if pad_n is not None:
            print('Pad', pad_n, 'aftertouch with value', value)
        else:
            print('Channel aftertouch with value', value)

    @push2_python.on_pad_aftertouch(pad_n=36)
    def function(push, value):
        print('Pad 36 aftertouched with value', value)

    @push2_python.on_pad_aftertouch(pad_ij=(0,3))
    def function(push, value):
        print('Pad (0, 3) aftertouched with value', value)
    """
    return action_handler(ACTION_PAD_AFTERTOUCH, pad_n=pad_n, pad_ij=pad_ij)


def on_encoder_rotated(encoder_name=None):
    """Shortcut for registering handlers for ACTION_ENCODER_ROTATED events.
    Optional "encoder_name" argument is to link the handler to a specific encoder.
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Encoder name (string, only if pad not specified in decorator)
        * Encoder increment (int, 1 for clockwise rotation and -1 for counter-clockwise)

    Examples:

    @push2_python.on_encoder_rotated()
    def function(push, encoder_name, increment):
        print('Encoder', encoder_name, 'rotated with increment', increment)

    @push2_python.on_encoder_rotated(push2_python.constants.ENCODER_TRACK1_ENCODER)
    def function(push, increment):
        print('Encoder for Track 1 rotated with increment', increment)
    """
    return action_handler(ACTION_ENCODER_ROTATED, encoder_name=encoder_name)


def on_encoder_touched(encoder_name=None):
    """Shortcut for registering handlers for ACTION_ENCODER_TOUCHED events.
    Optional "encoder_name" argument is to link the handler to a specific encoder.
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Encoder name (string, only if pad not specified in decorator)

    Examples:

    @push2_python.on_encoder_touched()
    def function(push, encoder_name):
        print('Encoder', encoder_name, 'touched')

    @push2_python.on_encoder_touched(push2_python.constants.ENCODER_TRACK1_ENCODER)
    def function(push):
        print('Encoder for Track 1 touched')
    """
    return action_handler(ACTION_ENCODER_TOUCHED, encoder_name=encoder_name)


def on_encoder_released(encoder_name=None):
    """Shortcut for registering handlers for ACTION_ENCODER_RELEASED events.
    Optional "encoder_name" argument is to link the handler to a specific encoder.
    Functions decorated with this decorator will be called with the following positional
    arguments:
        * Push2 object instance
        * Encoder name (string, only if pad not specified in decorator)

    Examples:

    @push2_python.on_encoder_released()
    def function(push, encoder_name):
        print('Encoder', encoder_name, 'released')

    @push2_python.on_encoder_released(push2_python.constants.ENCODER_TRACK1_ENCODER)
    def function(push):
        print('Encoder for Track 1 released')
    """
    return action_handler(ACTION_ENCODER_RELEASED, encoder_name=encoder_name)


def on_display_connected():
    """Shortcut for registering handlers for ACTION_DISPLAY_CONNECTED events.
    Functions decorated with this decorator will be called when push2-python successfully connects
    with the Push2 display and will have the following positional arguments:
        * Push2 object instance

    Examples:

    @push2_python.on_display_connected()
    def function(push):
        print('Display is ready to receive frames')
    """
    return action_handler(ACTION_DISPLAY_CONNECTED)


def on_display_disconnected():
    """Shortcut for registering handlers for ACTION_DISPLAY_DISCONNECTED events.
    Functions decorated with this decorator will be called when push2-python loses connection with the Push2 
    display. It will have the following positional arguments:
        * Push2 object instance

    Examples:

    @push2_python.on_display_disconnected()
    def function(push):
        print('Connection with Push2 display was just lost!')
    """
    return action_handler(ACTION_DISPLAY_DISCONNECTED)


def on_midi_connected():
    """Shortcut for registering handlers for ACTION_MIDI_CONNECTED events.
    Functions decorated with this decorator will be called when push2-python successfully connects
    with Push2 MIDI devices and will have the following positional arguments:
        * Push2 object instance

    Examples:

    @push2_python.on_midi_connected()
    def function(push):
        print('Push is ready to send and receive MIDI messages (set pad colors, buttons, advanced configuration, etc...)')
    """
    return action_handler(ACTION_MIDI_CONNECTED)


def on_midi_disconnected():
    """Shortcut for registering handlers for ACTION_MIDI_DISCONNECTED events.
    Functions decorated with this decorator will be called when push2-python loses MIDI connection with Push2.
    It will have the following positional arguments:
        * Push2 object instance

    Examples:

    @push2_python.on_midi_disconnected()
    def function(push):
        print('MIDI connection to push was just lost!')
    """
    return action_handler(ACTION_MIDI_DISCONNECTED)


def on_sustain_pedal():
    """Shortcut for registering handlers for ACTION_SUSTAIN_PEDAL events.
    Functions decorated with this decorator will be called when the sustain pedal connected to Push2 sustain
    pedal jack is either pressed or released. It will have the following positional arguments:
        * Push2 object instance
        * Sustain pedal state (True if sustain pedal was pressed, False if sustain pedal was released)

    Examples:

    @push2_python.on_sustain_pedal()
    def function(push, sustain_on):
        print('Sustain predal pressed' if sustain_on else 'Sustain predal released')
    """
    return action_handler(ACTION_SUSTAIN_PEDAL)
