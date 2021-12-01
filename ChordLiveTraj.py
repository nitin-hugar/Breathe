# Run Desired No. of Arms with Live Trajectory and Chord Manipulation

import os
import sys
import time
import csv
import socket
import queue
import numpy as np
from threading import Thread

# DEFINE Socket
SOCKET_HOST = '0.0.0.0'  # Standard loopback interface address (localhost)
SOCKET_PORT = 58299        # Port to listen on (non-privileged ports are > 1023)

def setup():
    for a in arms:
        a.set_simulation_robot(on_off=False)
        # a.motion_enable(enable=True)
        a.clean_warn()
        a.clean_error()
        a.set_mode(0)
        a.set_state(0)
        a.set_servo_angle(angle=[0.0, 0.0, 0.0, 1.57, 0.0, 0, 0.0], wait=False, speed=0.4, acceleration=0.25, is_radian=True)

def cvt(path):
    return_vector = []
    for i in range(7 * len(arms)):
        return_vector.append(float(path[i]))
    return return_vector

def readFile(csvFile):
    flower = []
    with open(csvFile, newline='') as csvfile:
        paths_reader_j = csv.reader(csvfile, delimiter=',', quotechar='|')
        for path in paths_reader_j:
            flower.append(cvt(path))
    return flower

def playDance(step, que):
    length = len(step)

    for i in range(length):
        start_time = time.time()
        j_angles = (step[i])

        que.put(j_angles)

        tts = time.time() - start_time
        sleep = 0.006 - tts

        if tts > 0.006:
            sleep = 0

        print(tts)
        time.sleep(sleep)

def playRobot(que, arm):
    IP = [0, 0, 0, 90, 0, 0, 0]
    tf = 3

    # t0 = 0
    t = [0 for i in range(0, 7)]
    q_i = [0 for i in range(0, 7)]
    q_dot_i = [0 for i in range(0, 7)]
    q_dot_f = [0 for i in range(0, 7)]
    q_dotdot_i = [0 for i in range(0, 7)]
    q_dotdot_f = [0 for i in range(0, 7)]
    t_array = np.arange(0, tf, 0.006)
    p = [0, 0, 0, 90, 0, 0, 0]
    v = [0 for i in range(0, 7)]
    a = [0 for i in range(0, 7)]

    # j_angles = [0, 0, 0, 90, 0, 0, 0]

    while True:
        q = que.get()

        # print("\nDequeued")
        goal = q
        q_i = p
        # q_i = j_angles
        q_dot_i = [0, 0, 0, 0, 0, 0, 0]
        q_dotdot_i = [0, 0, 0, 0, 0, 0, 0]
        q_f = goal
        j = 0

        while j <= len(t_array):
            start_time = time.time()

            if que.empty() == False:
                goal = q.get()
                q_i = p
                q_dot_i = v
                q_dotdot_i = [0 for i in range(0, 7)]
                q_f = goal
                j = 0
                print("switch")
            if j == len(t_array):
                t = tf
            else:
                t = t_array[j]

            a0 = q_i
            a1 = q_dot_i
            a2 = []
            a3 = []
            a4 = []
            a5 = []

            for i in range(0, 7):
                a2.append(0.5 * q_dotdot_i[i])
                a3.append(1.0 / (2.0 * tf ** 3.0) * (
                        20.0 * (q_f[i] - q_i[i]) - (8.0 * q_dot_f[i] + 12.0 * q_dot_i[i]) * tf - (
                        3.0 * q_dotdot_f[i] - q_dotdot_i[i]) * tf ** 2.0))
                a4.append(1.0 / (2.0 * tf ** 4.0) * (
                        30.0 * (q_i[i] - q_f[i]) + (14.0 * q_dot_f[i] + 16.0 * q_dot_i[i]) * tf + (
                        3.0 * q_dotdot_f[i] - 2.0 * q_dotdot_i[i]) * tf ** 2.0))
                a5.append(1.0 / (2.0 * tf ** 5.0) * (
                        12.0 * (q_f[i] - q_i[i]) - (6.0 * q_dot_f[i] + 6.0 * q_dot_i[i]) * tf - (
                        q_dotdot_f[i] - q_dotdot_i[i]) * tf ** 2.0))

                p[i] = (a0[i] + a1[i] * t + a2[i] * t ** 2 + a3[i] * t ** 3 + a4[i] * t ** 4 + a5[i] * t ** 5)
                v[i] = (a1[i] + 2 * a2[i] * t + 3 * a3[i] * t ** 2 + 4 * a4[i] * t ** 3 + 5 * a5[i] * t ** 4)
                a[i] = (2 * a2[i] + 6 * a3[i] * t + 12 * a4[i] * t ** 2 + 20 * a5[i] * t ** 3)

            # j_angles = p
            arm.set_servo_angle_j(angles=p, is_radian=False)

            tts = time.time() - start_time
            sleep = 0.006 - tts

            if tts > 0.006:
                sleep = 0

            time.sleep(sleep)
            j += 1
            # if t == 1:
            # print(t, p, v, a)

        # print("\nFinished")

if __name__ == "__main__":
    # INITIALIZE Socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((SOCKET_HOST, SOCKET_PORT))
    s.listen()
    s.settimeout(None)
    conn, addr = s.accept()
    s.settimeout(None)

    # INITIALIZE Arms
    ROBOT = "xArms"
    PORT = 5004

    a1 = queue()
    a2 = queue()
    a3 = queue()
    a4 = queue()

    quay = [a1, a2, a3, a4]

    sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))
    from xarm.wrapper import XArmAPI

    arm1 = XArmAPI('192.168.1.236')
    arm2 = XArmAPI('192.168.1.203')
    arm3 = XArmAPI('192.168.1.215')
    arm4 = XArmAPI('192.168.1.244')

    arms = [arm1, arm2, arm3, arm4]
    totalArms = len(arms)

    # Load Dances
    directory = os.path.join(os.path.dirname(__file__), '../Trajectories2/')
    dances = []
    trajectories = sorted(os.listdir(directory))
    for filename in trajectories:
        if filename.endswith(".csv"):
            print(filename)
            currentDance = (readFile(os.path.join(directory, filename)))
            dances.append(currentDance)
            continue

    # Start Arms
    t1 = Thread(target=playRobot, args=(a1, arm1,))
    t2 = Thread(target=playRobot, args=(a2, arm2,))
    t3 = Thread(target=playRobot, args=(a3, arm3,))
    t4 = Thread(target=playRobot, args=(a4, arm4,))

    setup()
    repeat = input("do we need to repeat? [y/n]")
    if repeat == 'y':
        setup()
    for a in arms:
        a.set_mode(1)
        a.set_state(0)

    t1.start()
    t2.start()
    t3.start()
    t4.start()

    try:
        with conn:
            s.settimeout(None)
            print('Connected by', addr)
            while True:
                chord = conn.recv(1024).decode()
                if chord:
                    print(chord)
                    if chord == "major":
                        playDance(dances[22], a1)
                        playDance(dances[22], a2)

                    if chord == "minor":
                        playDance(dances[23], a3)
                        playDance(dances[23], a4)

                    if chord == "augmented":
                        playDance(dances[2], a1)
                        playDance(dances[2], a2)
                        playDance(dances[2], a3)
                        playDance(dances[2], a4)

                    if chord == "diminished":
                        playDance(dances[21], a1)
                        playDance(dances[21], a2)
                        playDance(dances[21], a3)
                        playDance(dances[21], a4)

    except socket.error as socketerror:
            s.close()  # Remember to close sockets after use!
            print("Error: ", socketerror)

    except KeyboardInterrupt:
        s.close()  # Remember to close sockets after use!
        print('Keyboard interrupt...')

    finally:
        s.close()  # Remember to close sockets after use!
        print("Exiting...")





