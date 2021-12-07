from __future__ import print_function

import librosa
from scipy.signal import butter, filtfilt, medfilt
# import matplotlib.pyplot as plt
import numpy as np
import pyaudio
import rtmidi
from threading import Thread
import logging
import sys
import time
import socket
import aubio
from queue import Queue
from numpy import interp

from rtmidi.midiconstants import NOTE_ON
from rtmidi.midiutil import open_midiinput

HOST = '192.168.2.2'  # The server's hostname or IP address
PORT = 58315       # The port used by the server

stop_flute = False

log = logging.getLogger('midiin_poll')
logging.basicConfig(level=logging.DEBUG)


def send_midi(channel, note, velocity):
    midiout = rtmidi.MidiOut()
    available_ports = midiout.get_ports()
    if available_ports:
        # midiout.open_port(0)
        midiout.open_port(0)
        # midiout.open_port(2)
        # midiout.open_port(3)

    else:
        midiout.open_virtual_port("My virtual output")
    with midiout:
        note_on = [channel, note, velocity]
        midiout.send_message(note_on)
    del midiout


def send_midi_sound(channel, note, velocity):
    midiout = rtmidi.MidiOut()
    available_ports = midiout.get_ports()
    if available_ports:
        # midiout.open_port(0)
        midiout.open_port(1)
        # midiout.open_port(2)
        # midiout.open_port(3)

    else:
        midiout.open_virtual_port("My virtual output")
    with midiout:
        note_on = [channel, note, velocity]
        midiout.send_message(note_on)
    del midiout


def midiPlayBack(notes):
    for note in notes:
        pitch = note[2]
        if pitch > 83:
            pitch = 83
        print(pitch)
        duration = note[1]
        if duration > 0.4:
            send_midi(0x90, pitch, velocity=100)
            send_midi_sound(0x90, pitch, velocity=100)
            time.sleep(note[1])
            # send_midi(0X90, pitch, velocity=0)
            # send_midi_sound(0X90, pitch, velocity=0)


class MyMidiHandler():

    def __init__(self):
        #################################### Setup MIDI ####################################
        # Prompts user for MIDI input port, unless a valid port number or name
        # is given as the first argument on the command line.
        # API backend defaults to ALSA on Linux.

        # self.port = sys.argv[1] if len(sys.argv) > 1 else None
        self.port = 2
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
            print("E-M\n")
            return "E-M"
        # c sharp minor
        elif (pitches_ascending[0] == 61 and pitches_ascending[1] == 64 and pitches_ascending[2] == 68):
            print("C#-m\n")
            return "C#-m"
        # A Major
        elif (pitches_ascending[0] == 57 and pitches_ascending[1] == 61 and pitches_ascending[2] == 64):
            print("A-M\n")
            return "A-M"
        # B Major
        elif (pitches_ascending[0] == 59 and pitches_ascending[1] == 63 and pitches_ascending[2] == 66):
            print("B-M\n")
            return "B-M"
        else:
            return "None\n"

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
                        # if deltatime <= 0.5:
                        #     q.put(note)
                        # else:
                        #     q = Queue()
                        # if deltatime <= 1:
                        if note >= 57 and note <= 71:
                            q.put(note)
                            # print(note)
                    if q.qsize() > 2:
                        # print(deltatime)
                        # if deltatime <= 1:
                        # chord = self.determineTriads(q)
                        chord = self.determineTriadsPerformance(q)
                        # q = Queue()
                        s.sendall(chord.encode('UTF-8'))
                        # else:
                        q = Queue()

        except KeyboardInterrupt:
            s.close()
            print('Exiting')

        finally:
            s.close()
            print("Exit.")
            self.midiin.close_port()
            del self.midiin

def playFlute(playback_time):
    def freq2midi(freq):
        midi = 69 + 12 * np.log2(freq / 440)
        return np.asarray(midi, dtype=np.int32)

    def midi_to_notes(midi, fs, hop, smooth, minduration):
        # smooth midi pitch sequence first
        if (smooth > 0):
            filter_duration = smooth  # in seconds
            filter_size = int(filter_duration * fs / float(hop))
            if filter_size % 2 == 0:
                filter_size += 1
            midi_filt = medfilt(midi, filter_size)
        else:
            midi_filt = midi
        # print(len(midi),len(midi_filt))

        notes = []
        p_prev = 0
        duration = 0
        onset = 0
        for n, p in enumerate(midi_filt):
            if p == p_prev:
                duration += 1
            else:
                # treat 0 as silence
                if p_prev > 0:
                    # add note
                    duration_sec = duration * hop_s / float(fs)
                    # only add notes that are long enough
                    if duration_sec >= minduration:
                        onset_sec = onset * hop / float(fs)
                        notes.append((onset_sec, duration_sec, p_prev))

                # start new note
                onset = n
                duration = 1
                p_prev = p

        # add last note
        if p_prev > 0:
            # add note
            duration_sec = duration * hop / float(fs)
            onset_sec = onset * hop / float(fs)
            notes.append((onset_sec, duration_sec, p_prev))

        return notes

    def synthPlayBack(audio_block, hop_s, samplerate):
        # Load audio file
        y = audio_block
        sr = samplerate

        # low pass filter_audio
        filter_order = 4
        frequency = 1000.
        lowpass_f = frequency / (sr / 2.)
        b, a = butter(filter_order, lowpass_f, 'low')
        filtered_melody = filtfilt(b, a, y)

        # get fundamental contour
        #     f0_lowpass, voiced_flag_low, voiced_probs_low = librosa.pyin(audio_block, fmin=librosa.note_to_hz('B3'), fmax=librosa.note_to_hz('B5'), sr=samplerate,hop_length=hop_s)
        f0_lowpass, voiced_flag_low, voiced_probs_low = librosa.pyin(audio_block, fmin=librosa.note_to_hz('B3'),
                                                                     fmax=librosa.note_to_hz('B5'), sr=samplerate,
                                                                     hop_length=hop_s)

        midiNotes = freq2midi(f0_lowpass)
        midiNotes[midiNotes < 58] = 0
        # c_major = np.array([48, 50, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71, 72])
        #     e_major = np.array([59, 61, 63, 64, 66, 68, 69, 71, 73, 75, 76, 78, 80, 81, 83])
        scale = np.array([59, 61, 63, 64, 66, 68, 69, 71, 73, 75, 76, 78, 80, 81, 83])
        midi_quantized = np.empty_like(midiNotes)
        for i in range(midiNotes.shape[0]):
            if midiNotes[i] > 0:
                midi_quantized[i] = min(scale, key=lambda x: abs(x - midiNotes[i]))
            else:
                midiNotes[i] = 0

        notes = midi_to_notes(midi_quantized, samplerate, hop_s, smooth=0.40, minduration=0.1)
        midiPlayBack(notes)
        # synthSound = additive(notes, hop_s, samplerate)
        # print(notes)
        # sd.play(synthSound, samplerate)
        # sd.wait()

        return notes

    silence_flag = False
    pyaudio_format = pyaudio.paFloat32
    n_channels = 1
    samplerate = 44100
    silenceThresholdindB = -40
    win_s = 1024  # fft size
    hop_s = 512  # hop size
    fs = 44100

    p = pyaudio.PyAudio()

    # open stream
    stream = p.open(format=pyaudio_format,
                    channels=n_channels,
                    rate=samplerate,
                    input=True,
                    frames_per_buffer=hop_s)

    print("*** starting recording\n")
    audio_block = np.array([], dtype=np.float32)
    section_pitches = np.array([])
    section_onsets = np.array([])
    record_time = playback_time

    while True:
        global stop_flute
        if stop_flute:
            stop_flute = False
            break

        print("Record\n")
        # record a short phrase
        for i in range(0, int(samplerate / hop_s * record_time)):
            audiobuffer = stream.read(hop_s, exception_on_overflow=False)
            signal = np.frombuffer(audiobuffer, dtype=np.float32)
            audio_block = np.append(audio_block, signal)

        # channel1 = data_array[1::n_channels]

        print("Playback\n")
        synthPlayBack(audio_block, hop_s, samplerate)
        #         midiPlayBack(notes)
        audio_block = np.array([])

    stream.stop_stream()
    stream.close()
    p.terminate()

def playDrums():

    def extract_energy(audio_block, thresholdindB):
        global silence_count, silence_flag
        rms = np.sqrt(np.mean(np.square(audio_block)))
        dB = 10 * np.log10(rms)
        if dB < thresholdindB:
            silence_count += 1
            if silence_count > (blocksPerBeat * 4):
                silence_flag = True
            else:
                silence_flag = False
        else:
            silence_count = 0
            silence_flag = False

        return dB, silence_flag

    def scale_values(source_low, source_high, dest_low, dest_high, data):
        # m = interp1d([source_low, source_high], [dest_low, dest_high])
        m = interp(data, [source_low, source_high], [dest_low, dest_high])
        return int(m)

    silence_flag = False
    silence_count = 0
    # initialise pyaudio
    p = pyaudio.PyAudio()
    buffer_size = 1024
    # open stream

    pyaudio_format = pyaudio.paFloat32
    n_channels = 1
    samplerate = 44100
    stream = p.open(format=pyaudio_format,
                    channels=n_channels,
                    rate=samplerate,
                    input=True,
                    frames_per_buffer=buffer_size)

    # setup pitch
    tolerance = 0.8
    threshold = 0.2
    win_s = 2048  # fft size
    hop_s = buffer_size  # hop size

    onset_o = aubio.onset("mkl", win_s, hop_s, samplerate)
    onset_o.set_silence(-60.0)
    onset_o.set_threshold(threshold)

    tempo_o = aubio.tempo("default", win_s, hop_s, samplerate)
    tempo_o.set_threshold(threshold)

    print("*** starting recording\n")

    blockedEnergies = []
    TEMPO = 80
    tempo_time = [0]
    current_tempo = []
    blocksPerBeat = (60 / TEMPO) * (samplerate / hop_s)
    onset_count = 0
    energyTrack = 0
    # scale = [48, 50, 52, 53, 55, 57, 59, 60]
    count = 0
    while True:

        try:
            audiobuffer = stream.read(buffer_size)
            signal = np.frombuffer(audiobuffer, dtype=np.float32)

            onset = onset_o(signal)
            tempo = tempo_o(signal)

            if onset:
                print("onset\n")
                onset_count = 1
                # send_midi(0x92, 60, 127) # Channel 3

            # Get energy
            energyIndB, silence_flag = extract_energy(signal, -28.0)
            blockedEnergies.append(energyIndB)
            if len(blockedEnergies) == int(blocksPerBeat):
                energyAverage = np.sum(blockedEnergies) / blocksPerBeat
                energyTrack = energyAverage
                blockedEnergies = []

            if onset_count == 1 and not silence_flag:
                if tempo:
                    # tempo_time.append(time.time())
                    # TEMPO = int(60/abs(tempo_time[-1] - tempo_time[-2]))
                    send_midi(0x91, 80, scale_values(-23., -17., 10, 40, energyTrack))  # Channel 2
                    print(energyTrack)
                    count += 1

        except KeyboardInterrupt:
            print("*** Ctrl+C pressed, exiting\n")
            break

    print("*** done recording\n")
    stream.stop_stream()
    stream.close()
    p.terminate()

if __name__ == "__main__":
    midi_keyboard = MyMidiHandler()
    t_midi = Thread(target=midi_keyboard.on_midi_command, args=())
    t_midi.start()

    t_flute = Thread(target=playFlute, args=(10,))
    t_drums = Thread(target=playDrums, args=())

    input("Press a key to play flute:\n")
    t_flute.start()


    input("Press a key to play drums:\n")
    stop_flute = True
    t_flute.join()
    t_drums.start()

    # midiout = rtmidi.MidiOut()
    # available_ports = midiout.get_ports()
    # print(available_ports)

    # for i in range(10):
    #     send_midi(0x90, 60, 100)
    #     # send_midi_sound(0x90, 60, 100)
    #     time.sleep(2)
    #     send_midi(0x90, 64, 100)
    #     time.sleep(2)
    #     send_midi(0x90, 69, 100)
    #     time.sleep(2)
    #     # send_midi_sound(0x90, 83, 100)







