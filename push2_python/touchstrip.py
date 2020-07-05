import mido
import weakref
from .constants import MIDO_PITCWHEEL, MIDO_CONTROLCHANGE, ACTION_TOUCHSTRIP_TOUCHED, PUSH2_SYSEX_PREFACE_BYTES, PUSH2_SYSEX_END_BYTES
from .classes import AbstractPush2Section


class Push2TouchStrip(AbstractPush2Section):
    """Class to interface with Ableton's Touch Strip.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#Touch%20Strip
    """

    def set_modulation_wheel_mode(self):
        """Configure touchstrip to act as a modulation wheel
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#2101-touch-strip-configuration
        """
        msg = mido.Message.from_bytes(PUSH2_SYSEX_PREFACE_BYTES + [0x17, 0x0C] + PUSH2_SYSEX_END_BYTES)
        self.push.send_midi_to_push(msg)

    def set_pitch_bend_mode(self):
        """Configure touchstrip to act as a pitch bend wheel (this is the default)
        See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#2101-touch-strip-configuration
        """
        msg = mido.Message.from_bytes(PUSH2_SYSEX_PREFACE_BYTES + [0x17, 0x68] + PUSH2_SYSEX_END_BYTES)
        self.push.send_midi_to_push(msg)

    def on_midi_message(self, message):
        if message.type == MIDO_PITCWHEEL:
            value = message.pitch
            self.push.trigger_action(ACTION_TOUCHSTRIP_TOUCHED, value)
            return True
        elif message.type == MIDO_CONTROLCHANGE:
            value = message.value
            self.push.trigger_action(ACTION_TOUCHSTRIP_TOUCHED, value)
            return True
