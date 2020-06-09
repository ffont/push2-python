import mido
import weakref
from .constants import MIDI_PITCWHEEL, ACTION_TOUCHSTRIP_TOUCHED
from .classes import AbstractPush2Section


class Push2TouchStrip(AbstractPush2Section):
    """Class to interface with Ableton's Touch Strip.
    See https://github.com/Ableton/push-interface/blob/master/doc/AbletonPush2MIDIDisplayInterface.asc#Touch%20Strip
    """

    def on_midi_message(self, message):
        if message.type == MIDI_PITCWHEEL:
            value = message.pitch
            self.push.trigger_action(ACTION_TOUCHSTRIP_TOUCHED, value)
            return True
