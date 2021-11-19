import numpy as np
import queue
from threading import Thread
import time
from xarm.wrapper import XArmAPI


def setup():
    for a in arms:
        a.set_simulation_robot(on_off=False)
        # a.motion_enable(enable=True)
        a.clean_warn()
        a.clean_error()
        a.set_mode(0)
        a.set_state(0)
        a.set_servo_angle(angle=[0.0, 0.0, 0.0, 1.57, 0.0, 0, 0.0], wait=False, speed=0.4, acceleration=0.25, is_radian=True)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    arm6 = XArmAPI('192.168.1.211')
    arms = [arm6]
    setup()
    repeat = input("do we need to repeat? [y/n]")
    if repeat == 'y':
        setup()

    arm6.set_mode(1)
    arm6.set_state(0)


    def changeDir():
        while True:
            pos = list(map(int, input("\nEnter the positions for joints 1-7 : ").strip().split()))[:7]
            que.put(pos)


    que = queue.Queue()
    t2 = Thread(target=changeDir)
    t2.start()
    IP = [0, 0, 0, 90, 0, 0, 0]
    tf = 3

    # pos1 = [0, 30, 0, 90, 0, 45, 90]
    # pos2 = [0, 0, 0, 90, 0, 45, 0]
    #
    # que.put(pos1)
    # que.put(pos2)
    #
    # print("Queued positions")
    # time.sleep(3)

    t0 = 0
    t = t0
    q_i = 0
    q_dot_i = 0
    q_dot_f = 0
    q_dotdot_i = 0
    q_dotdot_f = 0
    t_array = np.arange(0, tf, 0.006)
    p = 0
    v = 0
    a = 0

    j_angles = [0, 0, 0, 90, 0, 0, 0]

    while True:
        q = que.get()
        for joint in range(0, 7):
            goal = q[6 - joint]

            # q_i = p
            q_i = j_angles[6 - joint]
            q_dot_i = 0
            q_dotdot_i = 0
            q_f = goal
            i = 0
            print(joint)
            while i <= len(t_array):
                start_time = time.time()
                if joint > 6:
                    goal = q[6 - joint]
                    q_i = p
                    q_dot_i = v
                    q_dotdot_i = 0
                    q_f = goal
                    i = 0
                    # IF YOU WANT TO ADD SPEED CHANGES THEN SWAP THE ABOVE LINES WITH THE BELOW LINES
                    # # q should input an array of [*absolute* position of joint, time(in seconds) to reach there]
                    # q_f = goal[0]
                    # tf = goal[1]
                    # t_array = np.arange(0, tf, 0.006)
                    print("switch")
                if i == len(t_array):
                    t = tf
                else:
                    t = t_array[i]
                a0 = q_i
                a1 = q_dot_i
                a2 = 0.5 * q_dotdot_i
                a3 = 1.0 / (2.0 * tf ** 3.0) * (20.0 * (q_f - q_i) - (8.0 * q_dot_f + 12.0 * q_dot_i) * tf - (
                            3.0 * q_dotdot_f - q_dotdot_i) * tf ** 2.0)
                a4 = 1.0 / (2.0 * tf ** 4.0) * (30.0 * (q_i - q_f) + (14.0 * q_dot_f + 16.0 * q_dot_i) * tf + (
                            3.0 * q_dotdot_f - 2.0 * q_dotdot_i) * tf ** 2.0)
                a5 = 1.0 / (2.0 * tf ** 5.0) * (12.0 * (q_f - q_i) - (6.0 * q_dot_f + 6.0 * q_dot_i) * tf - (
                            q_dotdot_f - q_dotdot_i) * tf ** 2.0)

                p = a0 + a1 * t + a2 * t ** 2 + a3 * t ** 3 + a4 * t ** 4 + a5 * t ** 5
                v = a1 + 2 * a2 * t + 3 * a3 * t ** 2 + 4 * a4 * t ** 3 + 5 * a5 * t ** 4
                a = 2 * a2 + 6 * a3 * t + 12 * a4 * t ** 2 + 20 * a5 * t ** 3
                j_angles[6 - joint] = p
                # print(j_angles)
                # arm6.set_servo_angle_j(angles=[0, 0, 0, 90, 0, p, 0], is_radian=False)
                arm6.set_servo_angle_j(angles=j_angles, is_radian=False)
                tts = time.time() - start_time
                sleep = 0.006 - tts

                if tts > 0.006:
                    sleep = 0

                # print(tts)
                time.sleep(sleep)
                i += 1
                # if t == 1:
                # print(t, p, v, a)
            print("done")
            time.sleep(0.5)