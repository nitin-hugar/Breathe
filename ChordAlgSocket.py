# Author: Hardik Goel
# Date Modified: 10/20/2021
# Project: Generative Gestures


from __future__ import print_function

import logging
import sys
import time
import socket
from queue import Queue

from rtmidi.midiconstants import NOTE_ON
from rtmidi.midiutil import open_midiinput

HOST = '0.0.0.0'  # The server's hostname or IP address
PORT = 58301       # The port used by the server

log = logging.getLogger('midiin_poll')
logging.basicConfig(level=logging.DEBUG)

class MyMidiHandler():

    def __init__(self):
        #################################### Setup MIDI ####################################
        # Prompts user for MIDI input port, unless a valid port number or name
        # is given as the first argument on the command line.
        # API backend defaults to ALSA on Linux.

        self.port = sys.argv[1] if len(sys.argv) > 1 else None
        try:
            self.midiin, self.port_name = open_midiinput(self.port)

        except (EOFError, KeyboardInterrupt):
            sys.exit()

        self.NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        self.OCTAVES = list(range(11))
        self.NOTES_IN_OCTAVE = len(self.NOTES)

    def number_to_note(self, number: int) -> tuple:
        octave = number // self.NOTES_IN_OCTAVE
        assert octave in self.OCTAVES
        assert 0 <= number <= 127
        note = self.NOTES[number % self.NOTES_IN_OCTAVE]
        return note, octave

    def note_to_number(self, note: str, octave: int) -> int:
        assert note in self.NOTES
        assert octave in self.OCTAVES
        note = self.NOTES.index(note)
        note += (self.NOTES_IN_OCTAVE * octave)
        assert 0 <= note <= 127
        return note

    def determineTriads(self, q):
        pitch1 = q.get()
        pitch2 = q.get()
        pitch3 = q.get()

        # sort pitches into a ascending order
        pitches = [pitch1, pitch2, pitch3]
        pitches_ascending = sorted(pitches)
        print(pitches_ascending)
        # find differences between pitches, normalizing across octaves
        interval1 = ((pitches_ascending[1] - pitches_ascending[0]) % 12)
        interval2 = ((pitches_ascending[2] - pitches_ascending[1]) % 12)

        # check for major triad
        if (interval1 == 4 and interval2 == 3) or (interval1 == 3 and interval2 == 5) or (
                interval1 == 5 and interval2 == 4):
            # print("major")
            return "major"
        # check for minor triad
        elif (interval1 == 3 and interval2 == 4) or (interval1 == 4 and interval2 == 5) or (
                interval1 == 5 and interval2 == 3):
            # print("minor")
            return "minor"
        # check for augmented triad
        elif (interval1 == 4 and interval2 == 4) or (interval1 == 4 and interval2 == 4) or (
                interval1 == 4 and interval2 == 4):
            # print("augmented")
            return "augmented"
        # check for diminished triad
        elif (interval1 == 3 and interval2 == 3) or (interval1 == 3 and interval2 == 6) or (
                interval1 == 6 and interval2 == 3):
            # print("diminished")
            return "diminished"

        else:
            return "none"

    def determineTriadsPerformance(self, q):
        pitch1 = q.get()
        pitch2 = q.get()
        pitch3 = q.get()

        pitches = [pitch1, pitch2, pitch3]
        pitches_ascending = sorted(pitches)

        # E Major
        if (pitches_ascending[0] == 64 and pitches_ascending[1] == 68 and pitches_ascending[2] == 71):
            print("E\n")
            return "E-M"
        # c sharp minor
        elif (pitches_ascending[0] == 61 and pitches_ascending[1] == 64 and pitches_ascending[2] == 68):
            print("C\n")
            return "C#-m"
        # A Major
        elif (pitches_ascending[0] == 57 and pitches_ascending[1] == 61 and pitches_ascending[2] == 64):
            print("A\n")
            return "A-M"
        # B Major
        elif (pitches_ascending[0] == 59 and pitches_ascending[1] == 63 and pitches_ascending[2] == 66):
            print("B\n")
            return "B-M"
        else:
            return "none"

    def on_midi_command(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(None)
        s.connect((HOST, PORT))
        s.settimeout(None)

        q = Queue()

        try:
            while True:
                event = self.midiin.get_message()
                if event:
                    message, deltatime = event
                    if message[0] & 0xF0 == NOTE_ON:
                        status, note, velocity = message
                        # note = self.number_to_note(note)
                        # print(note[0])
                        if q.qsize() > 2:
                            # print(deltatime)
                            # if deltatime <= 1:
                            # chord = self.determineTriads(q)
                            chord = self.determineTriadsPerformance(q)
                            q = Queue()
                            s.sendall(chord.encode('UTF-8'))
                            # else:
                            #     q = Queue()
                        if deltatime <= 0.5:
                            q.put(note)
                        else:
                            q = Queue()

        except KeyboardInterrupt:
            s.close()
            print('Exiting')

        finally:
            s.close()
            print("Exit.")
            self.midiin.close_port()
            del self.midiin

if __name__ == "__main__":
    midi = MyMidiHandler()
    midi.on_midi_command()


