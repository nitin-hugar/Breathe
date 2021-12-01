# Author: Hardik Goel
# Date Modified: 10/20/2021
# Project: Generative Gestures


import os
import sys
import time
import csv
import pdb
from queue import Queue
from threading import Thread
import time
import socket

SOCKET_HOST = '0.0.0.0'  # Standard loopback interface address (localhost)
SOCKET_PORT = 58299        # Port to listen on (non-privileged ports are > 1023)

def cvt(path):
    return_vector = []
    for i in range(7 * len(arms)):
        return_vector.append(float(path[i]))
    return return_vector


def playDance(step):
    length = len(step)

    for i in range(length):
        start_time = time.time()
        j_angles = (step[i])
        # b=6
        # arms[b].set_servo_angle_j(angles=j_angles[(b * 7):((b + 1) * 7)], is_radian=False)

        for b in range(totalArms):
            arms[b].set_servo_angle_j(angles=j_angles[(b * 7):((b + 1) * 7)], is_radian=False)
        tts = time.time() - start_time
        sleep = 0.006 - tts

        if tts > 0.006:
            sleep = 0

        print(tts)
        time.sleep(sleep)


def readFile(csvFile):
    flower = []
    with open(csvFile, newline='') as csvfile:
        paths_reader_j = csv.reader(csvfile, delimiter=',', quotechar='|')
        for path in paths_reader_j:
            flower.append(cvt(path))
    return flower


def setup():
    for a in arms:
        a.set_simulation_robot(on_off=False)
        # a.motion_enable(enable=True)
        a.clean_warn()
        a.clean_error()
        a.set_mode(0)
        a.set_state(0)
        a.set_servo_angle(angle=[0.0, 0.0, 0.0, 1.57, 0.0, 0, 0.0], wait=False, speed=0.4, acceleration=0.25,
                        is_radian=True)


if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((SOCKET_HOST, SOCKET_PORT))
    s.listen()
    s.settimeout(None)
    conn, addr = s.accept()
    s.settimeout(None)

    ROBOT = "xArms"
    PORT = 5004

    sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))
    from xarm.wrapper import XArmAPI

    arm1 = XArmAPI('192.168.1.236')
    arm2 = XArmAPI('192.168.1.203')
    arm3 = XArmAPI('192.168.1.215')
    arm4 = XArmAPI('192.168.1.244')
    arm5 = XArmAPI('192.168.1.208')
    arm6 = XArmAPI('192.168.1.242')
    arm7 = XArmAPI('192.168.1.204')
    arm8 = XArmAPI('192.168.1.226')
    arm9 = XArmAPI('192.168.1.234')
    arm10 = XArmAPI('192.168.1.237')

    arms = [arm1, arm2, arm3, arm4, arm5, arm6, arm7, arm8, arm9, arm10]
    totalArms = len(arms)

    # Using relative path to retrieve dances
    directory = os.path.join(os.path.dirname(__file__), '../Trajectories2/')

    # directory = '/home/codmusic/Desktop/FOREST/Trajectories2/'
    dances = []
    trajectories = sorted(os.listdir(directory))
    for filename in trajectories:
        if filename.endswith(".csv"):
            print(filename)
            currentDance = (readFile(os.path.join(directory, filename)))
            dances.append(currentDance)
            continue

    setup()
    repeat = input("do we need to repeat? [y/n]")
    if repeat == 'y':
        setup()
    for a in arms:
        a.set_mode(1)
        a.set_state(0)

    try:
        with conn:
            s.settimeout(None)
            print('Connected by', addr)
            while True:
                chord = conn.recv(1024).decode()
                if chord:
                    print(chord)
                    if chord == "major":
                        # playDance(dances[8])
                        playDance(dances[22])
                    if chord == "minor":
                        # playDance(dances[13])
                        playDance(dances[23])
                    if chord == "augmented":
                        playDance(dances[2])

                    if chord == "diminished":
                        playDance(dances[21])

    except socket.error as socketerror:
        s.close()  # Remember to close sockets after use!
        print("Error: ", socketerror)

    except KeyboardInterrupt:
        s.close()  # Remember to close sockets after use!
        print('Keyboard interrupt...')

    finally:
        s.close()  # Remember to close sockets after use!
        print("Exiting...")

