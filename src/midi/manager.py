
import mido
import logging
from threading import Thread

class MidiManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.current_port = None
        self.input_port_name = None
        self.callback = None
        self.listening = False

    def get_input_devices(self):
        """Returns a list of available MIDI input device names."""
        try:
            return mido.get_input_names()
        except Exception as e:
            self.logger.error(f"Error listing MIDI devices: {e}")
            return []

    def open_port(self, port_name):
        """Opens a MIDI input port by name."""
        try:
            if self.current_port:
                self.close_port()

            self.input_port_name = port_name
            # callback=self._mid_callback handles messages in a separate thread usually provided by backend
            # mido.open_input with callback uses a backend-specific thread.
            self.current_port = mido.open_input(port_name, callback=self._midi_callback)
            self.listening = True
            self.logger.info(f"Opened MIDI port: {port_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error opening MIDI port {port_name}: {e}")
            return False

    def close_port(self):
        """Closes the currently open port."""
        if self.current_port:
            try:
                self.current_port.close()
                self.listening = False
                self.current_port = None
                self.logger.info("Closed MIDI port.")
            except Exception as e:
                self.logger.error(f"Error closing MIDI port: {e}")

    def set_callback(self, callback):
        """Sets the external callback function for MIDI events (note_on)."""
        self.callback = callback

    def _midi_callback(self, msg):
        """Internal callback to filter and forward messages."""
        if not self.listening:
            return
        
        # We process 'note_on' with velocity > 0 as presses
        # And 'note_off' OR 'note_on' with velocity == 0 as releases
        if msg.type == 'note_on' and msg.velocity > 0:
            if self.callback:
                # Pass note number, velocity, and is_note_on flag
                self.callback(msg.note, msg.velocity, True)
        elif msg.type == 'note_off' or (msg.type == 'note_on' and getattr(msg, 'velocity', 0) == 0):
            if self.callback:
                self.callback(msg.note, 0, False)
        # Process 'control_change' (buttons, pads, faders)
        elif msg.type == 'control_change':
            if self.callback:
                # Typically control change sends value 127 for press and 0 for release, 
                # but it depends on the controller. We will treat value > 0 as a press.
                is_press = msg.value > 0
                self.callback(f"CC_{msg.control}", msg.value, is_press)
        # Process System Real-Time transport controls (Play, Stop, Continue)
        elif msg.type in ['start', 'stop', 'continue']:
            if self.callback:
                self.callback(f"SYS_{msg.type.upper()}", 127, True)
                # Auto-release immediately since system messages are pulses
                self.callback(f"SYS_{msg.type.upper()}", 0, False)
        # Process MIDI Machine Control (MMC) SysEx messages
        elif msg.type == 'sysex':
            if self.callback and len(msg.data) >= 3:
                # Standard MMC SysEx signature: [127, <device_id>, 6, <command>]
                if msg.data[0] == 127 and msg.data[2] == 6:
                    command = msg.data[3]
                    cmd_name = "UNKNOWN"
                    if command == 1: cmd_name = "STOP"
                    elif command == 2: cmd_name = "PLAY"
                    elif command == 3: cmd_name = "DEFERRED_PLAY"
                    elif command == 4: cmd_name = "FAST_FORWARD"
                    elif command == 5: cmd_name = "REWIND"
                    elif command == 6: cmd_name = "RECORD_STROBE"
                    elif command == 7: cmd_name = "RECORD_EXIT"
                    elif command == 8: cmd_name = "RECORD_PAUSE"
                    elif command == 9: cmd_name = "PAUSE"
                    
                    self.callback(f"MMC_{cmd_name}", 127, True)
                    # Auto-release immediately
                    self.callback(f"MMC_{cmd_name}", 0, False)
