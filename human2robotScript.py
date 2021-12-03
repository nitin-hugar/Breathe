import librosa
from scipy.signal import butter, filtfilt, medfilt
# import matplotlib.pyplot as plt
import numpy as np
import math
import pyaudio
import sounddevice as sd
import time
import rtmidi
# from pynput import keyboard
# import sched
# import sys


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


def synthPlayBack(audio_block,hop_s, samplerate):
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
    f0_lowpass, voiced_flag_low, voiced_probs_low = librosa.pyin(audio_block, fmin=librosa.note_to_hz('B3'), fmax=librosa.note_to_hz('B5'), sr=samplerate,hop_length=hop_s)

    midiNotes = freq2midi(f0_lowpass)
    midiNotes[midiNotes < 58] = 0
    # c_major = np.array([48, 50, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69, 71, 72])
#     e_major = np.array([59, 61, 63, 64, 66, 68, 69, 71, 73, 75, 76, 78, 80, 81, 83])
    scale = np.array([59, 61, 63, 64, 66, 68, 69, 71, 73, 75, 76, 78, 80, 81, 83])
    midi_quantized = np.empty_like(midiNotes)
    for i in range(midiNotes.shape[0]):
        if midiNotes[i] > 0:
            midi_quantized[i] = min(scale, key=lambda x:abs(x-midiNotes[i]))
        else: 
            midiNotes[i] = 0
    
    notes = midi_to_notes(midi_quantized, samplerate, hop_s, smooth=0.40, minduration=0.1)
    midiPlayBack(notes)
    # synthSound = additive(notes, hop_s, samplerate)
    # print(notes)
    # sd.play(synthSound, samplerate)
    # sd.wait()
    
    return notes


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
        print(pitch)
        duration = note[1]
        if duration > 0.4: 
            send_midi(0x90, pitch, velocity=100)
            send_midi_sound(0x90, pitch, velocity=100)
            time.sleep(note[1])
            # send_midi(0X90, pitch, velocity=0)
            # send_midi_sound(0X90, pitch, velocity=0)
        


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

print("*** starting recording")
audio_block = np.array([], dtype=np.float32)
section_pitches = np.array([])
section_onsets = np.array([])
record_time = 10


while True:
    try:
        print("Record")
        # record a short phrase
        for i in range(0, int(samplerate / hop_s * record_time)):
            audiobuffer = stream.read(hop_s, exception_on_overflow=False)
            signal = np.frombuffer(audiobuffer, dtype=np.float32)
            audio_block = np.append(audio_block, signal)

        #channel1 = data_array[1::n_channels]

        print("Playback")
        synthPlayBack(audio_block, hop_s, samplerate)
#         midiPlayBack(notes)
        audio_block = np.array([])



    except KeyboardInterrupt:
        print("***Ending Stream")
        break



stream.stop_stream()
stream.close()
p.terminate()

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
