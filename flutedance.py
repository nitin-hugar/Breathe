from rtpmidi import RtpMidi
from pymidi import server
import os
import sys
import time
from queue import Queue
from threading import Thread
import time
import numpy as np
from numpy import interp
import socket

# DEFINE Socket
SOCKET_HOST = '192.168.2.2'  # Standard loopback interface address (localhost)
SOCKET_PORT = 58315  # Port to listen on (non-privileged ports are > 1023)


def setup():
    for a in arms:
        a.set_simulation_robot(on_off=False)
        # a.motion_enable(enable=True)
        a.clean_warn()
        a.clean_error()
        a.set_mode(0)
        a.set_state(0)
        a.set_servo_angle(angle=[0.0, 0.0, 0.0, 90, 0.0, 0.0, 0.0], wait=False, speed=20, acceleration=5,
                          is_radian=False)


class MyHandler(server.Handler):
    def on_peer_connected(self, peer):
        # Handler for peer connected
        print('Peer connected: {}'.format(peer))

    def on_peer_disconnected(self, peer):
        # Handler for peer disconnected
        print('Peer disconnected: {}'.format(peer))

    def on_midi_commands(self, peer, command_list):
        # Handler for midi msgs
        for command in command_list:
            chn = command.channel
            if chn == 0:  # Channel 1
                if command.command == 'note_on':
                    key = command.params.key.__int__()
                    q_pitch.put(key)
                    # print("singsingsing FROM THE TABLETOP")
            if chn == 1:  # Channel 2
                if command.command == 'note_on':
                    tempo = command.params.key.__int__()
                    energy = command.params.velocity
                    q_tempo.put(np.array([tempo, energy]))
                    print("grooooovy")
            # if chn == 2:  # Channel 3!!!!!
            #     if command.command == 'note_on':
            #         if command.params.key.__int__() == 60:
            #             q2.put(0)
            #             # print("onset baby!")
            #         else:
            #             print("F in chat")
            #             # print(chn)
            #             key = command.params.key
            #             velocity = command.params.velocity
            #             # print('key {} with velocity {}'.format(key, velocity))
            #             q.put(velocity)

            # playDance(dances[velocity])


def onset(in_q2):  # third q system
    armsused = [arm5, arm8, arm9, arm10, arm7]
    targets = [0, 0, 0, 0, 0]
    numbot = len(targets)
    positions = [60, 80]
    robotcounter = 0
    positioncounter = 0
    for b in range(numbot):
        armsused[b].set_mode(0)
        armsused[b].set_state(0)
        armsused[b].set_servo_angle(angle=[0.0, -4.0, 0.0, 165, 0.0, 80, 0.0], wait=False, speed=20, acceleration=5,
                                    is_radian=False)
    while True:
        in_q2.get()
        currentbot = robotcounter % numbot
        currentpos = positions[positioncounter % 2]
        targets[currentbot] = currentpos

        if robotcounter % numbot == (numbot - 1):
            positioncounter += 1
        # print("current bot is:", currentbot, "current pose is:", currentpos)
        armsused[currentbot].set_servo_angle(angle=[0.0, -4.0, 0.0, 165, 0.0, currentpos, 0.0], wait=False,
                                             speed=130, acceleration=80, is_radian=False)
        robotcounter += 1


def tempo(in_q3):
    tempoArms = [arm1, arm4, arm5, arm6, arm7]
    ups = [arm1, arm4, arm6]
    downs = [arm5, arm7]
    for a in tempoArms:
        a.set_mode(0)
        a.set_state(0)
        # print("moving")
        a.set_servo_angle(angle=[0.0, -60.0, 0.0, 60, 0.0, 30, 0.0], wait=False, speed=40, acceleration=50,
                          is_radian=False)
        a.set_position(*[121, -1, 505, -2, -86, -170], wait=True)

    counter = 0
    while True:
        goal = in_q3.get()
        height = goal[1]
        min_h = 10
        max_h = 40
        # height = ((height - 60) * (max_h - min_h) / 10) + min_h
        if height > max_h:
            height = max_h
        elif height < min_h:
            height = min_h
        direction = (-1) ** counter
        j2 = -75 + height
        j6 = 90 - abs(j2)
        j4 = 90 + j2 + j6
        speed = j4 / 0.6
        if direction > 0:
            for a in ups:
                a.set_servo_angle(angle=[0.0, j2, 0.0, j4, 0.0, j6, 0.0], wait=False, speed=speed,
                                  acceleration=50, is_radian=False)
            for a in downs:
                a.set_servo_angle(angle=[0.0, -60, 0.0, 60, 0.0, 30, 0.0], wait=False, speed=speed,
                                  acceleration=50, is_radian=False)
        else:
            for a in ups:
                a.set_servo_angle(angle=[0.0, -60, 0.0, 60, 0.0, 30, 0.0], wait=False, speed=speed,
                                  acceleration=50, is_radian=False)
            for a in downs:
                a.set_servo_angle(angle=[0.0, j2, 0.0, j4, 0.0, j6, 0.0], wait=False, speed=speed,
                                  acceleration=50, is_radian=False)
        counter += 1


def pitchContour(in_q4):
    pitcharm = [arm6]
    for a in pitcharm:
        a.set_servo_angle(angle=[0.0, -50, 0.0, 40, 0.0, 30, 0.0], wait=True, speed=20,
                          acceleration=10, is_radian=False)
        a.set_position(*[200, 0, 620, 180, -89, 0], wait=False)
    # 55 - 80 range
    # 550-900
    max_h = 900
    min_h = 500
    # print("Start the loop")
    while True:
        pitch = in_q4.get()
        height = interp(pitch, [59, 83], [500, 900])
        # height = ((pitch - 48) * (max_h - min_h) / 12) + min_h
        if height > 900:
            height = 900
        if height < 500:
            height = 500

        for a in pitcharm:
            print(pitch)
            a.set_position(*[200, 0, height, 180, -89, 0], speed=8400, wait=False)


def playRobot(que, arm):
    IP = [0, 0, 0, 90, 0, 0, 0]
    tf = 50

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
        # print(q)
        # print("\nDequeued")

        goal = q
        q_i = p
        # q_i = j_angles
        q_dot_i = [0, 0, 0, 0, 0, 0, 0]
        q_dotdot_i = [0, 0, 0, 0, 0, 0, 0]
        q_f = goal
        j = 0

        while j < len(t_array):
            start_time = time.time()

            if abs(p[0] - q_f[0]) < 1.0 and abs(p[1] - q_f[1]) < 1.0 and abs(p[2] - q_f[2]) < 1.0 and abs(
                    p[3] - q_f[3]) < 1.0 and abs(p[4] - q_f[4]) < 1.0 and abs(p[5] - q_f[5]) < 1.0 and abs(
                p[6] - q_f[6]) < 1.0:
                break

            # if que.empty() == False:
            #     q = que.get
            #     goal = q
            #     q_i = p
            #     q_dot_i = v
            #     q_dotdot_i = [0 for i in range(0, 7)]
            #     q_f = goal
            #     j = 0
            #     # IF YOU WANT TO ADD SPEED CHANGES THEN SWAP THE ABOVE LINES WITH THE BELOW LINES
            #     # # q should input an array of [*absolute* position of joint, time(in seconds) to reach there]
            #     # q_f = goal[0]
            #     # tf = goal[1]
            #     # t_array = np.arange(0, tf, 0.006)
            #     print("switch")
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
            # print(f"{p} {arm}")

            tts = time.time() - start_time
            sleep = 0.006 - tts

            if tts > 0.006:
                sleep = 0

            time.sleep(sleep)
            j += 1
            # if t == 1:
            # print(t, p, v, a)

        # print(f"\nFinished {arm}")


def changeDir(q, pos):
    # while True:
    # pos = list(map(int, input("\nEnter the positions for joints 1-7 : ").strip().split()))[:7]
    # time.sleep(5)
    # pos = [0, 0, 0, 90, 0, 90, 0]
    q.put(pos)


if __name__ == "__main__":
    # INITIALIZE Socket
    print("Sockets Init\n")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((SOCKET_HOST, SOCKET_PORT))
    s.listen()
    s.settimeout(None)
    conn, addr = s.accept()
    print("Socket done\n")
    s.settimeout(None)

    # INITIALIZE Arms
    ROBOT = "xArms"
    PORT = 5004

    sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))
    from xarm.wrapper import XArmAPI

    arm1 = XArmAPI('192.168.1.208')
    arm2 = XArmAPI('192.168.1.244')
    arm3 = XArmAPI('192.168.1.203')
    arm4 = XArmAPI('192.168.1.236')
    arm5 = XArmAPI('192.168.1.226')
    arm6 = XArmAPI('192.168.1.242')
    arm7 = XArmAPI('192.168.1.215')
    arm8 = XArmAPI('192.168.1.234')
    # arm9 = XArmAPI('192.168.1.237')
    arm10 = XArmAPI('192.168.1.204')

    arms = [arm1, arm2, arm3, arm4, arm5, arm6, arm7, arm8, arm10]

    totalArms = len(arms)

    setup()
    repeat = input("do we need to repeat? [y/n]")
    if repeat == 'y':
        setup()

    set_arms = [arm2, arm3, arm8, arm10]

    for a in set_arms:
        a.set_mode(1)
        a.set_state(0)

    ############################################# MIDI Keyboard #############################################

    # Direction queues
    arm2_q = Queue()
    arm3_q = Queue()
    arm8_q = Queue()
    arm10_q = Queue()
    que_pos = [arm2_q, arm3_q, arm8_q, arm10_q]

    # Live Traj Threads for Arms
    t_midi_a1 = Thread(target=playRobot, args=(arm2_q, arm2))
    t_midi_a2 = Thread(target=playRobot, args=(arm3_q, arm3))
    t_midi_a3 = Thread(target=playRobot, args=(arm8_q, arm8))
    t_midi_a4 = Thread(target=playRobot, args=(arm10_q, arm10))

    # Live Traj Thread
    # t_liveTraj = Thread(target=changeDir, args=(que_pos,))

    # Start Threads
    # t_liveTraj.start()
    t_midi_a1.start()
    t_midi_a2.start()
    t_midi_a3.start()
    t_midi_a4.start()

    ############################################# MIR Band ###################################################
    # Create the shared queue
    # q_onset = Queue()
    q_tempo = Queue()
    q_pitch = Queue()

    # Create Threads
    rtp_midi = RtpMidi(ROBOT, MyHandler(), PORT)
    rt = Thread(target=rtp_midi.run, args=())

    # t_onset = Thread(target=onset, args=(q_onset,))
    t_tempo = Thread(target=tempo, args=(q_tempo,))
    t_pitch = Thread(target=pitchContour, args=(q_pitch,))

    # Start Threads
    # t_onset.start()
    t_tempo.start()
    t_pitch.start()
    rt.start()

    ############################################# Start MIDI Performance ########################################

    chord_pos = {
        "E-M": {
            "arm2": [0, 0, 135, 130, 0, 50, 0],
            "arm3": [0, 0, -103, 130, 0, 50, 0],
            "arm8": [0, 0, 60, 130, 0, 50, 0],
            "arm10": [0, 0, -8.5, 130, 0, 50, 0]
        },
        "C#-m": {
            "arm2": [-36, -40, 180, 150, 0, 20, 0],
            "arm3": [42, -40, 180, 150, 0, 20, 0],
            "arm8": [-110, -40, 180, 150, 0, 20, 0],
            "arm10": [158, -40, 180, 150, 0, 20, 0]
        },
        "A-M": {
            "arm2": [-36, 40, 180, 110, 0, 80, 0],
            "arm3": [42, 40, 180, 110, 0, 80, 0],
            "arm8": [-110, 40, 180, 110, 0, 80, 0],
            "arm10": [158, 40, 180, 110, 0, 80, 0]
        },
        "B-M": {
            "arm2": [-180, 60, 180, 50, 0, 28, 0],
            "arm3": [-180, 60, 180, 50, 0, 28, 0],
            "arm8": [-8, 60, 180, 50, 0, 28, 0],
            "arm10": [-8, 60, 180, 50, 0, 28, 0]
        }
    }

    try:
        with conn:
            s.settimeout(None)
            print('Connected by', addr)
            while True:
                chord = conn.recv(1024).decode()
                print(chord)
                if chord in chord_pos.keys():
                    changeDir(arm2_q, chord_pos.get(chord).get("arm2"))
                    changeDir(arm3_q, chord_pos.get(chord).get("arm3"))
                    changeDir(arm8_q, chord_pos.get(chord).get("arm8"))
                    changeDir(arm10_q, chord_pos.get(chord).get("arm10"))

                # if chord == "E-M":
                #     print("E-M\n")
                #     changeDir(arm2_q, [0, 0, 135, 130, 0, 50, 0])
                # if chord == "C#-m":
                #     print("C#-m\n")
                #     # changeDir(que_pos, [105, 43, -61, 125, -76, 70, 25])
                #     changeDir(arm2_q,[-36, -40, 180, 150, 0, 20, 0])
                # if chord == "A-M":
                #     print("A-M\n")
                #     # changeDir(que_pos, [-35, -115, -175, 190, -7.5, -12, 25])
                #     changeDir(arm2_q, [-36, 40, 180, 110, 0, 80, 0])
                # if chord == "B-M":
                #     print("B-M\n")
                #     # changeDir(que_pos, [-60, 75, 255, 151, -17, 30, 25])
                #     changeDir(arm2_q, [-180, 60, 180, 50, 0, 20, 0])

    except socket.error as socketerror:
        s.close()  # Remember to close sockets after use!
        print("Error: ", socketerror)

    except KeyboardInterrupt:
        s.close()  # Remember to close sockets after use!
        print('Keyboard interrupt...')

    finally:
        s.close()  # Remember to close sockets after use!
        print("Exiting...")
