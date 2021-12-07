#!/usr/bin/env python3
# Software License Agreement (BSD License)
#
# Copyright (c) 2018, UFACTORY, Inc.
# All rights reserved.
#
# Author: Jimy Zhang <jimy.zhang@ufactory.cc> <jimy92@163.com>
# Author: Vinman <vinman.wen@ufactory.cc> <vinman.cub@gmail.com>

import time
import threading
import functools
from ..utils import convert
from ..config.x_config import XCONF


def lock_require(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        with args[0].lock:
            return func(*args, **kwargs)
    return decorator


class UxbusCmd(object):
    BAUDRATES = (4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600,
                 1000000, 1500000, 2000000, 2500000)

    def __init__(self):
        self._has_error = False
        self._has_warn = False
        self._state_is_ready = False
        self._error_code = 0
        self._warn_code = 0
        self._cmd_num = 0
        self._debug = False
        self.lock = threading.Lock()
        self._GET_TIMEOUT = XCONF.UxbusConf.GET_TIMEOUT / 1000
        self._SET_TIMEOUT = XCONF.UxbusConf.SET_TIMEOUT / 1000
        self._last_comm_time = time.time()

    @property
    def last_comm_time(self):
        return self._last_comm_time

    @property
    def state_is_ready(self):
        return self._state_is_ready

    def set_timeout(self, timeout):
        try:
            if isinstance(timeout, (tuple, list)):
                if len(timeout) >= 2:
                    self._SET_TIMEOUT = timeout[0] if timeout[0] > 0 else self._SET_TIMEOUT
                    self._GET_TIMEOUT = timeout[1] if timeout[1] > 0 else self._GET_TIMEOUT
                elif len(timeout) == 1:
                    self._SET_TIMEOUT = timeout[0] if timeout[0] > 0 else self._SET_TIMEOUT
                    self._GET_TIMEOUT = timeout[0] if timeout[0] > 0 else self._GET_TIMEOUT
            elif isinstance(timeout, (int, float)):
                self._SET_TIMEOUT = timeout if timeout > 0 else self._SET_TIMEOUT
                self._GET_TIMEOUT = timeout if timeout > 0 else self._GET_TIMEOUT
        except:
            pass
        return [self._SET_TIMEOUT, self._GET_TIMEOUT] if self._SET_TIMEOUT != self._GET_TIMEOUT else self._SET_TIMEOUT

    def set_debug(self, debug):
        self._debug = debug

    def check_xbus_prot(self, data, funcode):
        raise NotImplementedError

    def send_pend(self, funcode, num, timeout):
        raise NotImplementedError

    def send_xbus(self, funcode, txdata, num):
        raise NotImplementedError

    @lock_require
    def set_nu8(self, funcode, datas, num, timeout=None):
        ret = self.send_xbus(funcode, datas, num)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP]
        return self.send_pend(funcode, 0, self._SET_TIMEOUT if timeout is None else timeout)

    @lock_require
    def set_get_nu8(self, funcode, datas, num_send, num_get):
        ret = self.send_xbus(funcode, datas, num_send)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP]
        return self.send_pend(funcode, num_get, self._SET_TIMEOUT)

    @lock_require
    def get_nu8(self, funcode, num):
        ret = self.send_xbus(funcode, 0, 0)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (num + 1)
        return self.send_pend(funcode, num, self._GET_TIMEOUT)

    @lock_require
    def set_nu16(self, funcode, datas, num):
        hexdata = convert.u16s_to_bytes(datas, num)
        ret = self.send_xbus(funcode, hexdata, num * 2)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP]
        ret = self.send_pend(funcode, 0, self._SET_TIMEOUT)
        return ret

    @lock_require
    def get_nu16(self, funcode, num):
        ret = self.send_xbus(funcode, 0, 0)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (num * 2 + 1)
        ret = self.send_pend(funcode, num * 2, self._GET_TIMEOUT)
        data = [0] * (1 + num)
        data[0] = ret[0]
        data[1:num] = convert.bytes_to_u16s(ret[1:num * 2 + 1], num)
        return data

    @lock_require
    def set_nfp32(self, funcode, datas, num):
        hexdata = convert.fp32s_to_bytes(datas, num)
        ret = self.send_xbus(funcode, hexdata, num * 4)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP]
        return self.send_pend(funcode, 0, self._SET_TIMEOUT)

    @lock_require
    def set_nfp32_with_bytes(self, funcode, datas, num, additional_bytes, rx_len=0):
        hexdata = convert.fp32s_to_bytes(datas, num)
        hexdata += additional_bytes
        ret = self.send_xbus(funcode, hexdata, num * 4 + len(additional_bytes))
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP]
        return self.send_pend(funcode, rx_len, self._SET_TIMEOUT)

    @lock_require
    def set_nint32(self, funcode, datas, num):
        hexdata = convert.int32s_to_bytes(datas, num)
        ret = self.send_xbus(funcode, hexdata, num * 4)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP]
        return self.send_pend(funcode, 0, self._SET_TIMEOUT)

    @lock_require
    def get_nfp32(self, funcode, num, timeout=None):
        ret = self.send_xbus(funcode, 0, 0)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (num * 4 + 1)
        ret = self.send_pend(funcode, num * 4, timeout if timeout is not None else self._GET_TIMEOUT)
        data = [0] * (1 + num)
        data[0] = ret[0]
        data[1:num] = convert.bytes_to_fp32s(ret[1:num * 4 + 1], num)
        return data

    @lock_require
    def swop_nfp32(self, funcode, datas, txn, rxn):
        hexdata = convert.fp32s_to_bytes(datas, txn)
        ret = self.send_xbus(funcode, hexdata, txn * 4)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (rxn + 1)
        ret = self.send_pend(funcode, rxn * 4, self._GET_TIMEOUT)
        data = [0] * (1 + rxn)
        data[0] = ret[0]
        data[1:rxn+1] = convert.bytes_to_fp32s(ret[1:rxn * 4 + 1], rxn)
        return data

    @lock_require
    def is_nfp32(self, funcode, datas, txn):
        hexdata = convert.fp32s_to_bytes(datas, txn)
        ret = self.send_xbus(funcode, hexdata, txn * 4)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * 2
        return self.send_pend(funcode, 1, self._GET_TIMEOUT)

    def get_version(self):
        return self.get_nu8(XCONF.UxbusReg.GET_VERSION, 40)

    def get_robot_sn(self):
        return self.get_nu8(XCONF.UxbusReg.GET_ROBOT_SN, 40)

    def check_verification(self):
        # txdata = signature, 175: signature length if use 14-character SN for plain text, do not miss '\n's
        return self.get_nu8(XCONF.UxbusReg.CHECK_VERIFY, 1)

    def shutdown_system(self, value):
        txdata = [value]
        return self.set_nu8(XCONF.UxbusReg.SHUTDOWN_SYSTEM, txdata, 1)

    def set_record_traj(self, value):
        txdata = [value]
        return self.set_nu8(XCONF.UxbusReg.SET_TRAJ_RECORD, txdata, 1)

    def playback_traj(self, value, spdx=1):
        txdata = [value, spdx]
        return self.set_nint32(XCONF.UxbusReg.PLAY_TRAJ, txdata, 2)

    def playback_traj_old(self, value):
        txdata = [value]
        return self.set_nint32(XCONF.UxbusReg.PLAY_TRAJ, txdata, 1)

    def save_traj(self, filename, wait_time=2):
        char_list = list(filename)
        txdata = [ord(i) for i in char_list]
        name_len = len(txdata)
        if name_len > 80:
            print("name length should not exceed 80 characters!")
            return [XCONF.UxbusState.ERR_PARAM]
        txdata = txdata + [0] * (81 - name_len)

        ret = self.set_nu8(XCONF.UxbusReg.SAVE_TRAJ, txdata, 81)
        time.sleep(wait_time)  # Must! or buffer would be flushed if set mode to pos_mode
        return ret

    def load_traj(self, filename, wait_time=2):
        char_list = list(filename)
        txdata = [ord(i) for i in char_list]
        name_len = len(txdata)
        if name_len > 80:
            print("name length should not exceed 80 characters!")
            return [XCONF.UxbusState.ERR_PARAM]
        txdata = txdata + [0] * (81 - name_len)

        ret = self.set_nu8(XCONF.UxbusReg.LOAD_TRAJ, txdata, 81)
        time.sleep(wait_time)  # Must! or buffer would be flushed if set mode to pos_mode
        return ret

    def get_traj_rw_status(self):
        return self.get_nu8(XCONF.UxbusReg.GET_TRAJ_RW_STATUS, 1)

    def set_reduced_mode(self, on_off):
        txdata = [on_off]
        return self.set_nu8(XCONF.UxbusReg.SET_REDUCED_MODE, txdata, 1)

    def set_reduced_linespeed(self, lspd_mm):
        txdata = [lspd_mm]
        return self.set_nfp32(XCONF.UxbusReg.SET_REDUCED_TRSV, txdata, 1)

    def set_reduced_jointspeed(self, jspd_rad):
        txdata = [jspd_rad]
        return self.set_nfp32(XCONF.UxbusReg.SET_REDUCED_P2PV, txdata, 1)

    def get_reduced_mode(self):
        return self.get_nu8(XCONF.UxbusReg.GET_REDUCED_MODE, 1)

    def get_reduced_states(self, length=21):
        ret = self.get_nu8(XCONF.UxbusReg.GET_REDUCED_STATE, length)
        msg = [0] * 8
        msg[0] = ret[0]
        msg[1] = ret[1]  # reduced_mode_is_on
        msg[2] = convert.bytes_to_16s(ret[2:14], 6)  # tcp_boundary
        msg[3:5] = convert.bytes_to_fp32s(ret[14:22], 2)  # tcp_speed, joint_speed
        if length == 79:
            msg[5] = convert.bytes_to_fp32s(ret[22:78], 14)  # joint range
            msg[6:8] = ret[78:80]  # fense_is_on, collision_rebound
        return msg

    def set_xyz_limits(self, xyz_list):
        return self.set_nint32(XCONF.UxbusReg.SET_LIMIT_XYZ, xyz_list, 6)

    def set_timer(self, sec_later, timer_id, fun_code, param1=0, param2=0):
        txdata = [sec_later, timer_id, fun_code, param1, param2]
        return self.set_nint32(XCONF.UxbusReg.SET_TIMER, txdata, 5)

    def cancel_timer(self, timer_id):
        txdata = [timer_id]
        return self.set_nint32(XCONF.UxbusReg.CANCEL_TIMER, txdata, 1)

    def set_world_offset(self, pose_offset):
        return self.set_nfp32(XCONF.UxbusReg.SET_WORLD_OFFSET, pose_offset, 6)

    def cnter_reset(self):
        return self.set_nu8(XCONF.UxbusReg.CNTER_RESET, 0, 0)

    def cnter_plus(self):
        return self.set_nu8(XCONF.UxbusReg.CNTER_PLUS, 0, 0)

    def set_reduced_jrange(self, jrange_rad):
        return self.set_nfp32(XCONF.UxbusReg.SET_REDUCED_JRANGE, jrange_rad, 14)

    def set_fense_on(self, on_off):
        txdata = [on_off]
        return self.set_nu8(XCONF.UxbusReg.SET_FENSE_ON, txdata, 1)

    def set_collis_reb(self, on_off):
        txdata = [on_off]
        return self.set_nu8(XCONF.UxbusReg.SET_COLLIS_REB, txdata, 1)

    def motion_en(self, axis_id, enable):
        txdata = [axis_id, int(enable)]
        return self.set_nu8(XCONF.UxbusReg.MOTION_EN, txdata, 2, timeout=self._SET_TIMEOUT if self._SET_TIMEOUT >= 2 else 2)

    def set_state(self, value):
        txdata = [value]
        return self.set_nu8(XCONF.UxbusReg.SET_STATE, txdata, 1)

    def get_state(self):
        return self.get_nu8(XCONF.UxbusReg.GET_STATE, 1)

    def get_cmdnum(self):
        return self.get_nu16(XCONF.UxbusReg.GET_CMDNUM, 1)

    def get_err_code(self):
        return self.get_nu8(XCONF.UxbusReg.GET_ERROR, 2)

    def get_hd_types(self):
        return self.get_nu8(XCONF.UxbusReg.GET_HD_TYPES, 2)

    def reload_dynamics(self):
        return self.set_nu8(XCONF.UxbusReg.RELOAD_DYNAMICS, 0, 0)

    def clean_err(self):
        return self.set_nu8(XCONF.UxbusReg.CLEAN_ERR, 0, 0)

    def clean_war(self):
        return self.set_nu8(XCONF.UxbusReg.CLEAN_WAR, 0, 0)

    def set_brake(self, axis_id, enable):
        txdata = [axis_id, int(enable)]
        return self.set_nu8(XCONF.UxbusReg.SET_BRAKE, txdata, 2)

    def set_mode(self, mode):
        txdata = [mode]
        return self.set_nu8(XCONF.UxbusReg.SET_MODE, txdata, 1)

    def set_report_tau_or_i(self, tau_or_i):  # 0 for tau(default), 1 for i
        txdata = [tau_or_i]
        return self.set_nu8(XCONF.UxbusReg.REPORT_TAU_OR_I, txdata, 1)

    def get_report_tau_or_i(self):
        return self.get_nu8(XCONF.UxbusReg.GET_REPORT_TAU_OR_I, 1)

    def move_line(self, mvpose, mvvelo, mvacc, mvtime):
        txdata = [mvpose[i] for i in range(6)]
        txdata += [mvvelo, mvacc, mvtime]
        return self.set_nfp32(XCONF.UxbusReg.MOVE_LINE, txdata, 9)

    def move_line_aa(self, mvpose, mvvelo, mvacc, mvtime, mvcoord, relative):
        float_data = [mvpose[i] for i in range(6)]
        float_data += [mvvelo, mvacc, mvtime]
        byte_data = bytes([mvcoord, relative])
        return self.set_nfp32_with_bytes(XCONF.UxbusReg.MOVE_LINE_AA, float_data, 9, byte_data)

    def move_servo_cart_aa(self, mvpose, mvvelo, mvacc, tool_coord, relative):
        float_data = [mvpose[i] for i in range(6)]
        float_data += [mvvelo, mvacc, tool_coord]
        byte_data = bytes([relative])
        return self.set_nfp32_with_bytes(XCONF.UxbusReg.MOVE_SERVO_CART_AA, float_data, 9, byte_data)

    def get_position_aa(self):
        return self.get_nfp32(XCONF.UxbusReg.GET_TCP_POSE_AA, 6)

    @lock_require
    def get_pose_offset(self, pose1, pose2, orient_type_in=0, orient_type_out=0):
        float_data = [pose1[i] for i in range(6)]
        float_data += [pose2[j] for j in range(6)]
        byte_data = bytes([orient_type_in, orient_type_out])
        ret_fp_num = 6
        funcode = XCONF.UxbusReg.CAL_POSE_OFFSET
        hexdata = convert.fp32s_to_bytes(float_data, 12)
        hexdata += byte_data

        ret = self.send_xbus(funcode, hexdata, len(hexdata))
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (ret_fp_num * 4 + 1)

        ret = self.send_pend(funcode, ret_fp_num * 4, self._GET_TIMEOUT)
        data = [0] * (1 + ret_fp_num)
        data[0] = ret[0]
        data[1:ret_fp_num] = convert.bytes_to_fp32s(ret[1:ret_fp_num * 4 + 1], ret_fp_num)
        return data

    def move_line_tool(self, mvpose, mvvelo, mvacc, mvtime):
        txdata = [mvpose[i] for i in range(6)]
        txdata += [mvvelo, mvacc, mvtime]
        return self.set_nfp32(XCONF.UxbusReg.MOVE_LINE_TOOL, txdata, 9)

    def move_lineb(self, mvpose, mvvelo, mvacc, mvtime, mvradii):
        txdata = [mvpose[i] for i in range(6)]
        txdata += [mvvelo, mvacc, mvtime, mvradii]
        return self.set_nfp32(XCONF.UxbusReg.MOVE_LINEB, txdata, 10)

    def move_joint(self, mvjoint, mvvelo, mvacc, mvtime):
        txdata = [mvjoint[i] for i in range(7)]
        txdata += [mvvelo, mvacc, mvtime]
        return self.set_nfp32(XCONF.UxbusReg.MOVE_JOINT, txdata, 10)

    def move_jointb(self, mvjoint, mvvelo, mvacc, mvradii):
        txdata = [mvjoint[i] for i in range(7)]
        txdata += [mvvelo, mvacc, mvradii]
        return self.set_nfp32(XCONF.UxbusReg.MOVE_JOINTB, txdata, 10)

    def move_gohome(self, mvvelo, mvacc, mvtime):
        txdata = [mvvelo, mvacc, mvtime]
        return self.set_nfp32(XCONF.UxbusReg.MOVE_HOME, txdata, 3)

    def move_servoj(self, mvjoint, mvvelo, mvacc, mvtime):
        txdata = [mvjoint[i] for i in range(7)]
        txdata += [mvvelo, mvacc, mvtime]
        return self.set_nfp32(XCONF.UxbusReg.MOVE_SERVOJ, txdata, 10)

    def move_servo_cartesian(self, mvpose, mvvelo, mvacc, mvtime):
        txdata = [mvpose[i] for i in range(6)]
        txdata += [mvvelo, mvacc, mvtime]
        return self.set_nfp32(XCONF.UxbusReg.MOVE_SERVO_CART, txdata, 9)

    def set_servot(self, jnt_taus):
        txdata = [jnt_taus[i] for i in range(7)]
        return self.set_nfp32(XCONF.UxbusReg.SET_SERVOT, txdata, 7)

    def get_joint_tau(self):
        return self.get_nfp32(XCONF.UxbusReg.GET_JOINT_TAU, 7)

    def set_safe_level(self, level):
        txdata = [level]
        return self.set_nu8(XCONF.UxbusReg.SET_SAFE_LEVEL, txdata, 1)

    def get_safe_level(self):
        return self.get_nu8(XCONF.UxbusReg.GET_SAFE_LEVEL, 1)

    def sleep_instruction(self, sltime):
        txdata = [sltime]
        return self.set_nfp32(XCONF.UxbusReg.SLEEP_INSTT, txdata, 1)

    def move_circle(self, pose1, pose2, mvvelo, mvacc, mvtime, percent):
        txdata = [0] * 16
        for i in range(6):
            txdata[i] = pose1[i]
            txdata[6 + i] = pose2[i]
        txdata[12] = mvvelo
        txdata[13] = mvacc
        txdata[14] = mvtime
        txdata[15] = percent
        ret = self.set_nfp32(XCONF.UxbusReg.MOVE_CIRCLE, txdata, 16)
        return ret

    def set_tcp_jerk(self, jerk):
        txdata = [jerk]
        return self.set_nfp32(XCONF.UxbusReg.SET_TCP_JERK, txdata, 1)

    def set_tcp_maxacc(self, acc):
        txdata = [acc]
        return self.set_nfp32(XCONF.UxbusReg.SET_TCP_MAXACC, txdata, 1)

    def set_joint_jerk(self, jerk):
        txdata = [jerk]
        return self.set_nfp32(XCONF.UxbusReg.SET_JOINT_JERK, txdata, 1)

    def set_joint_maxacc(self, acc):
        txdata = [acc]
        return self.set_nfp32(XCONF.UxbusReg.SET_JOINT_MAXACC, txdata, 1)

    def set_tcp_offset(self, pose_offset):
        return self.set_nfp32(XCONF.UxbusReg.SET_TCP_OFFSET, pose_offset, 6)

    def set_tcp_load(self, load_mass, load_com):
        param_list = [load_mass]
        param_list.extend(load_com)
        return self.set_nfp32(XCONF.UxbusReg.SET_LOAD_PARAM, param_list, 4)

    def set_collis_sens(self, value):
        txdata = [value]
        return self.set_nu8(XCONF.UxbusReg.SET_COLLIS_SENS, txdata, 1)

    def set_teach_sens(self, value):
        txdata = [value]
        return self.set_nu8(XCONF.UxbusReg.SET_TEACH_SENS, txdata, 1)

    def set_gravity_dir(self, gravity_dir):
        return self.set_nfp32(XCONF.UxbusReg.SET_GRAVITY_DIR, gravity_dir, 3)

    def clean_conf(self):
        return self.set_nu8(XCONF.UxbusReg.CLEAN_CONF, 0, 0)

    def save_conf(self):
        return self.set_nu8(XCONF.UxbusReg.SAVE_CONF, 0, 0)

    def get_joint_pos(self):
        return self.get_nfp32(XCONF.UxbusReg.GET_JOINT_POS, 7)

    def get_tcp_pose(self):
        return self.get_nfp32(XCONF.UxbusReg.GET_TCP_POSE, 6)

    def get_ik(self, pose):
        return self.swop_nfp32(XCONF.UxbusReg.GET_IK, pose, 6, 7)

    def get_fk(self, angles):
        return self.swop_nfp32(XCONF.UxbusReg.GET_FK, angles, 7, 6)

    def is_joint_limit(self, joint):
        return self.is_nfp32(XCONF.UxbusReg.IS_JOINT_LIMIT, joint, 7)

    def is_tcp_limit(self, pose):
        return self.is_nfp32(XCONF.UxbusReg.IS_TCP_LIMIT, pose, 6)

    @lock_require
    def gripper_addr_w16(self, addr, value):
        txdata = bytes([XCONF.GRIPPER_ID])
        txdata += convert.u16_to_bytes(addr)
        txdata += convert.fp32_to_bytes(value)
        ret = self.send_xbus(XCONF.UxbusReg.TGPIO_W16B, txdata, 7)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (7 + 1)

        ret = self.send_pend(XCONF.UxbusReg.TGPIO_W16B, 0, self._GET_TIMEOUT)
        return ret

    @lock_require
    def gripper_addr_r16(self, addr):
        txdata = bytes([XCONF.GRIPPER_ID])
        txdata += convert.u16_to_bytes(addr)
        ret = self.send_xbus(XCONF.UxbusReg.TGPIO_R16B, txdata, 3)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (7 + 1)

        ret = self.send_pend(XCONF.UxbusReg.TGPIO_R16B, 4, self._GET_TIMEOUT)
        return [ret[0], convert.bytes_to_long_big(ret[1:5])]

    @lock_require
    def gripper_addr_w32(self, addr, value):
        txdata = bytes([XCONF.GRIPPER_ID])
        txdata += convert.u16_to_bytes(addr)
        txdata += convert.fp32_to_bytes(value)
        ret = self.send_xbus(XCONF.UxbusReg.TGPIO_W32B, txdata, 7)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (7 + 1)

        ret = self.send_pend(XCONF.UxbusReg.TGPIO_W32B, 0, self._GET_TIMEOUT)
        return ret

    @lock_require
    def gripper_addr_r32(self, addr):
        txdata = bytes([XCONF.GRIPPER_ID])
        txdata += convert.u16_to_bytes(addr)
        ret = self.send_xbus(XCONF.UxbusReg.TGPIO_R32B, txdata, 3)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (7 + 1)

        ret = self.send_pend(XCONF.UxbusReg.TGPIO_R32B, 4, self._GET_TIMEOUT)
        return [ret[0], convert.bytes_to_long_big(ret[1:5])]

    def gripper_set_en(self, value):
        return self.gripper_addr_w16(XCONF.ServoConf.CON_EN, value)

    def gripper_set_mode(self, value):
        return self.gripper_addr_w16(XCONF.ServoConf.CON_MODE, value)

    def gripper_set_zero(self):
        return self.gripper_addr_w16(XCONF.ServoConf.MT_ZERO, 1)

    def gripper_get_pos(self):
        return self.gripper_addr_r32(XCONF.ServoConf.CURR_POS)

    def gripper_set_pos(self, pulse):
        return self.gripper_addr_w32(XCONF.ServoConf.TAGET_POS, pulse)

    def gripper_set_posspd(self, speed):
        return self.gripper_addr_w16(XCONF.ServoConf.POS_SPD, speed)

    def gripper_get_errcode(self):
        ret = self.get_nu8(XCONF.UxbusReg.TGPIO_ERR, 2)
        return ret

    def gripper_clean_err(self):
        return self.gripper_addr_w16(XCONF.ServoConf.RESET_ERR, 1)

    @lock_require
    def tgpio_addr_w16(self, addr, value):
        txdata = bytes([XCONF.TGPIO_ID])
        txdata += convert.u16_to_bytes(addr)
        txdata += convert.fp32_to_bytes(value)
        ret = self.send_xbus(XCONF.UxbusReg.TGPIO_W16B, txdata, 7)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (7 + 1)

        ret = self.send_pend(XCONF.UxbusReg.TGPIO_W16B, 0, self._GET_TIMEOUT)
        return ret

    @lock_require
    def tgpio_addr_r16(self, addr):
        txdata = bytes([XCONF.TGPIO_ID])
        txdata += convert.u16_to_bytes(addr)
        ret = self.send_xbus(XCONF.UxbusReg.TGPIO_R16B, txdata, 3)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (7 + 1)

        ret = self.send_pend(XCONF.UxbusReg.TGPIO_R16B, 4, self._GET_TIMEOUT)
        ret1 = [0] * 2
        ret1[0] = ret[0]
        ret1[1] = convert.bytes_to_long_big(ret[1:5])
        return ret1

    @lock_require
    def tgpio_addr_w32(self, addr, value):
        txdata = bytes([XCONF.TGPIO_ID])
        txdata += convert.u16_to_bytes(addr)
        txdata += convert.fp32_to_bytes(value)
        ret = self.send_xbus(XCONF.UxbusReg.TGPIO_W32B, txdata, 7)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (7 + 1)

        ret = self.send_pend(XCONF.UxbusReg.TGPIO_W32B, 0, self._GET_TIMEOUT)
        return ret

    @lock_require
    def tgpio_addr_r32(self, addr):
        txdata = bytes([XCONF.TGPIO_ID])
        txdata += convert.u16_to_bytes(addr)
        ret = self.send_xbus(XCONF.UxbusReg.TGPIO_R32B, txdata, 3)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (7 + 1)

        ret = self.send_pend(XCONF.UxbusReg.TGPIO_R32B, 4, self._GET_TIMEOUT)
        ret1 = [0] * 2
        ret1[0] = ret[0]
        ret1[1] = convert.bytes_to_long_big(ret[1:5])
        return ret1

    def tgpio_get_digital(self):
        ret = self.tgpio_addr_r16(XCONF.ServoConf.DIGITAL_IN)
        value = [0] * 3
        value[0] = ret[0]
        value[1] = ret[1] & 0x0001
        value[2] = (ret[1] & 0x0002) >> 1
        return value

    def tgpio_set_digital(self, ionum, value):
        tmp = 0
        if ionum == 1:
            tmp = tmp | 0x0100
            if value:
                tmp = tmp | 0x0001
        elif ionum == 2:
            tmp = tmp | 0x0200
            if value:
                tmp = tmp | 0x0002
        else:
            return [-1, -1]
        return self.tgpio_addr_w16(XCONF.ServoConf.DIGITAL_OUT, tmp)

    def tgpio_get_analog1(self):
        ret = self.tgpio_addr_r16(XCONF.ServoConf.ANALOG_IO1)
        value = [0] * 2
        value[0] = ret[0]
        value[1] = ret[1] * 3.3 / 4095.0
        return value

    def tgpio_get_analog2(self):
        ret = self.tgpio_addr_r16(XCONF.ServoConf.ANALOG_IO2)
        value = [0] * 2
        value[0] = ret[0]
        value[1] = ret[1] * 3.3 / 4095.0
        return value

    def set_modbus_timeout(self, value):
        txdata = [int(value)]
        return self.set_nu16(XCONF.UxbusReg.TGPIO_MB_TIOUT, txdata, 1)

    def set_modbus_baudrate(self, baudrate):
        if baudrate not in self.BAUDRATES:
            return [-1, -1]
        ret = self.tgpio_addr_r16(XCONF.ServoConf.MODBUS_BAUDRATE & 0x0FFF)
        if ret[0] == 0:
            baud_val = self.BAUDRATES.index(baudrate)
            if ret[1] != baud_val:
                # self.tgpio_addr_w16(XCONF.ServoConf.MODBUS_BAUDRATE, baud_val)
                self.tgpio_addr_w16(0x1A0B, baud_val)
                time.sleep(0.3)
                return self.tgpio_addr_w16(XCONF.ServoConf.SOFT_REBOOT, 1)
        return ret[:2]

    @lock_require
    def tgpio_set_modbus(self, modbus_t, len_t):
        txdata = bytes([XCONF.TGPIO_ID])
        txdata += bytes(modbus_t)
        ret = self.send_xbus(XCONF.UxbusReg.TGPIO_MODBUS, txdata, len_t + 1)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (7 + 1)

        ret = self.send_pend(XCONF.UxbusReg.TGPIO_MODBUS, -1, self._GET_TIMEOUT)
        return ret

    @lock_require
    def tgpio_delay_set_digital(self, ionum, on_off, delay_sec):
        txdata = bytes([ionum, on_off])
        txdata += convert.fp32_to_bytes(delay_sec)
        ret = self.send_xbus(XCONF.UxbusReg.DELAYED_TGPIO_SET, txdata, 6)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP]
        return self.send_pend(XCONF.UxbusReg.DELAYED_TGPIO_SET, 0, self._SET_TIMEOUT)

    @lock_require
    def cgpio_delay_set_digital(self, ionum, on_off, delay_sec):
        txdata = bytes([ionum, on_off])
        txdata += convert.fp32_to_bytes(delay_sec)
        ret = self.send_xbus(XCONF.UxbusReg.DELAYED_CGPIO_SET, txdata, 6)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP]
        return self.send_pend(XCONF.UxbusReg.DELAYED_CGPIO_SET, 0, self._SET_TIMEOUT)

    @lock_require
    def cgpio_position_set_digital(self, ionum, on_off, xyz, tol_r):
        txdata = bytes([ionum, on_off])
        txdata += convert.fp32s_to_bytes(xyz, 3)
        txdata += convert.fp32_to_bytes(tol_r)
        ret = self.send_xbus(XCONF.UxbusReg.POSITION_CGPIO_SET, txdata, 18)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP]
        return self.send_pend(XCONF.UxbusReg.POSITION_CGPIO_SET, 0, self._SET_TIMEOUT)

    @lock_require
    def tgpio_position_set_digital(self, ionum, on_off, xyz, tol_r):
        txdata = bytes([ionum, on_off])
        txdata += convert.fp32s_to_bytes(xyz, 3)
        txdata += convert.fp32_to_bytes(tol_r)
        ret = self.send_xbus(XCONF.UxbusReg.POSITION_TGPIO_SET, txdata, 18)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP]
        return self.send_pend(XCONF.UxbusReg.POSITION_TGPIO_SET, 0, self._SET_TIMEOUT)

    @lock_require
    def cgpio_position_set_analog(self, ionum, value, xyz, tol_r):
        txdata = bytes([ionum])
        txdata += convert.u16_to_bytes(int(value / 10.0 * 4095.0))
        txdata += convert.fp32s_to_bytes(xyz, 3)
        txdata += convert.fp32_to_bytes(tol_r)
        ret = self.send_xbus(XCONF.UxbusReg.POSITION_CGPIO_SET_ANALOG, txdata, 19)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP]
        return self.send_pend(XCONF.UxbusReg.POSITION_CGPIO_SET_ANALOG, 0, self._SET_TIMEOUT)

    # io_type: 0 for CGPIO, 1 for TGPIO
    def config_io_stop_reset(self, io_type, on_off):
        txdata = [io_type, on_off]
        return self.set_nu8(XCONF.UxbusReg.SET_IO_STOP_RESET, txdata, 2)

    def gripper_modbus_w16s(self, addr, value, length):
        txdata = bytes([XCONF.GRIPPER_ID])
        txdata += bytes([0x10])
        txdata += convert.u16_to_bytes(addr)
        txdata += convert.u16_to_bytes(length)
        txdata += bytes([length * 2])
        txdata += value
        ret = self.tgpio_set_modbus(txdata, length * 2 + 7)
        return ret

    def gripper_modbus_r16s(self, addr, length):
        txdata = bytes([XCONF.GRIPPER_ID])
        txdata += bytes([0x03])
        txdata += convert.u16_to_bytes(addr)
        txdata += convert.u16_to_bytes(length)
        ret = self.tgpio_set_modbus(txdata, 6)
        return ret

    def gripper_modbus_set_en(self, value):
        value = convert.u16_to_bytes(int(value))
        return self.gripper_modbus_w16s(XCONF.ServoConf.CON_EN, value, 1)

    def gripper_modbus_set_mode(self, value):
        value = convert.u16_to_bytes(int(value))
        return self.gripper_modbus_w16s(XCONF.ServoConf.CON_MODE, value, 1)

    def gripper_modbus_set_zero(self):
        value = convert.u16_to_bytes(int(1))
        return self.gripper_modbus_w16s(XCONF.ServoConf.MT_ZERO, value, 1)

    def gripper_modbus_get_pos(self):
        ret = self.gripper_modbus_r16s(XCONF.ServoConf.CURR_POS, 2)
        ret1 = [0] * 2
        ret1[0] = ret[0]
        if ret[0] in [0, XCONF.UxbusState.ERR_CODE, XCONF.UxbusState.WAR_CODE] and len(ret) == 9:
            ret1[1] = convert.bytes_to_long_big(ret[5:9])
        else:
            if ret1[0] == 0:
                ret1[0] = XCONF.UxbusState.ERR_LENG
            # print('gripper_modbus_get_pos:', len(ret), ret)
        # print(ret1, ret)
        return ret1

    def gripper_modbus_set_pos(self, pulse):
        value = bytes([(int(pulse) >> 24) & 0xFF])
        value += bytes([(int(pulse) >> 16) & 0xFF])
        value += bytes([(int(pulse) >> 8) & 0xFF])
        value += bytes([int(pulse) & 0xFF])
        return self.gripper_modbus_w16s(XCONF.ServoConf.TAGET_POS, value, 2)

    def gripper_modbus_set_posspd(self, speed):
        speed = convert.u16_to_bytes(int(speed))
        return self.gripper_modbus_w16s(XCONF.ServoConf.POS_SPD, speed, 1)

    def gripper_modbus_get_errcode(self):
        ret = self.gripper_modbus_r16s(XCONF.ServoConf.ERR_CODE, 1)
        ret1 = [0] * 2
        ret1[0] = ret[0]
        if ret[0] in [0, XCONF.UxbusState.ERR_CODE, XCONF.UxbusState.WAR_CODE] and len(ret) == 7:
            ret1[1] = convert.bytes_to_u16(ret[5:7])
        else:
            if ret1[0] == 0:
                ret1[0] = XCONF.UxbusState.ERR_LENG
            # print('gripper_modbus_get_errcode:', len(ret), ret)
        # print(ret1, ret)
        return ret1

    def gripper_modbus_clean_err(self):
        value = convert.u16_to_bytes(int(1))
        return self.gripper_modbus_w16s(XCONF.ServoConf.RESET_ERR, value, 1)

    def servo_set_zero(self, axis_id):
        txdata = [int(axis_id)]
        ret = self.set_nu8(XCONF.UxbusReg.SERVO_ZERO, txdata, 1)
        return ret

    def servo_get_dbmsg(self):
        ret = self.get_nu8(XCONF.UxbusReg.SERVO_DBMSG, 16)
        return ret

    @lock_require
    def servo_addr_w16(self, axis_id, addr, value):
        txdata = bytes([axis_id])
        txdata += convert.u16_to_bytes(addr)
        txdata += convert.fp32_to_bytes(value)
        ret = self.send_xbus(XCONF.UxbusReg.SERVO_W16B, txdata, 7)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (7 + 1)

        ret = self.send_pend(XCONF.UxbusReg.SERVO_W16B, 0, self._GET_TIMEOUT)
        return ret

    @lock_require
    def servo_addr_r16(self, axis_id, addr):
        txdata = bytes([axis_id])
        txdata += convert.u16_to_bytes(addr)
        ret = self.send_xbus(XCONF.UxbusReg.SERVO_R16B, txdata, 3)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (7 + 1)

        ret = self.send_pend(XCONF.UxbusReg.SERVO_R16B, 4, self._GET_TIMEOUT)
        return [ret[0], convert.bytes_to_long_big(ret[1:5])]
        # return [ret[0], convert.bytes_to_long_big(ret[1:5])[0]]

    @lock_require
    def servo_addr_w32(self, axis_id, addr, value):
        txdata = bytes([axis_id])
        txdata += convert.u16_to_bytes(addr)
        txdata += convert.fp32_to_bytes(value)
        ret = self.send_xbus(XCONF.UxbusReg.SERVO_W32B, txdata, 7)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (7 + 1)

        ret = self.send_pend(XCONF.UxbusReg.SERVO_W32B, 0, self._GET_TIMEOUT)
        return ret

    @lock_require
    def servo_addr_r32(self, axis, addr):
        txdata = bytes([axis])
        txdata += convert.u16_to_bytes(addr)
        ret = self.send_xbus(XCONF.UxbusReg.SERVO_R32B, txdata, 3)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP] * (7 + 1)

        ret = self.send_pend(XCONF.UxbusReg.SERVO_R32B, 4, self._GET_TIMEOUT)
        return [ret[0], convert.bytes_to_long_big(ret[1:5])]
        # return [ret[0], convert.bytes_to_long_big(ret[1:5])[0]]

    # -----------------------------------------------------
    # controler gpio
    # -----------------------------------------------------
    def cgpio_get_auxdigit(self):
        ret = self.get_nu16(XCONF.UxbusReg.CGPIO_GET_DIGIT, 1)
        value = [0] * 2
        value[0] = ret[0]
        value[1] = ret[1]
        return value

    def cgpio_get_analog1(self):
        ret = self.get_nu16(XCONF.UxbusReg.CGPIO_GET_ANALOG1, 1)
        value = [0] * 2
        value[0] = ret[0]
        value[1] = ret[1] * 10.0 / 4095.0
        return value

    def cgpio_get_analog2(self):
        ret = self.get_nu16(XCONF.UxbusReg.CGPIO_GET_ANALOG2, 1)
        value = [0] * 2
        value[0] = ret[0]
        value[1] = ret[1] * 10.0 / 4095.0
        return value

    def cgpio_set_auxdigit(self, ionum, value):
        tmp = [0] * 2
        if ionum > 7:
            tmp[1] = tmp[1] | (0x0100 << (ionum - 8))
            if value:
                tmp[1] = tmp[1] | (0x0001 << (ionum - 8))
        else:
            tmp[0] = tmp[0] | (0x0100 << ionum)
            if value:
                tmp[0] = tmp[0] | (0x0001 << ionum)
        return self.set_nu16(XCONF.UxbusReg.CGPIO_SET_DIGIT, tmp, 2 if ionum > 7 else 1)
        # tmp = [0] * 1
        # tmp[0] = tmp[0] | (0x0100 << ionum)
        # if value:
        #     tmp[0] = tmp[0] | (0x0001 << ionum)
        # return self.set_nu16(XCONF.UxbusReg.CGPIO_SET_DIGIT, tmp, 1)

    def cgpio_set_analog1(self, value):
        txdata = [int(value / 10.0 * 4095.0)]
        return self.set_nu16(XCONF.UxbusReg.CGPIO_SET_ANALOG1, txdata, 1)

    def cgpio_set_analog2(self, value):
        txdata = [int(value / 10.0 * 4095.0)]
        return self.set_nu16(XCONF.UxbusReg.CGPIO_SET_ANALOG2, txdata, 1)

    def cgpio_set_infun(self, num, fun):
        txdata = [int(num), int(fun)]
        return self.set_nu8(XCONF.UxbusReg.CGPIO_SET_IN_FUN, txdata, 2)

    def cgpio_set_outfun(self, num, fun):
        txdata = [int(num), int(fun)]
        return self.set_nu8(XCONF.UxbusReg.CGPIO_SET_OUT_FUN, txdata, 2)

    def cgpio_get_state(self):
        # ret = self.get_nu8(XCONF.UxbusReg.CGPIO_GET_STATE, 34)
        # ret = self.get_nu8(XCONF.UxbusReg.CGPIO_GET_STATE, 50)
        ret = self.get_nu8(XCONF.UxbusReg.CGPIO_GET_STATE, -1)
        msg = [0] * 13
        msg[0] = ret[0]
        msg[1] = ret[1]
        msg[2] = ret[2]

        msg[3:11] = convert.bytes_to_u16s(ret[3:19], 8)
        msg[7] = msg[7] / 4095.0 * 10.0
        msg[8] = msg[8] / 4095.0 * 10.0
        msg[9] = msg[9] / 4095.0 * 10.0
        msg[10] = msg[10] / 4095.0 * 10.0
        msg[11] = ret[19:27]
        msg[12] = ret[27:35]
        if len(ret) >= 50:
            msg[11] = ret[19:27] + ret[35:43]
            msg[12] = ret[27:35] + ret[43:51]
        return msg

    def set_self_collision_detection(self, on_off):
        txdata = [on_off]
        return self.set_nu8(XCONF.UxbusReg.SET_SELF_COLLIS_CHECK, txdata, 1)

    def set_collision_tool_model(self, tool_type, params):
        if len(params) > 0:
            byte_data = bytes([tool_type])
            return self.set_nfp32_with_bytes(XCONF.UxbusReg.SET_COLLIS_TOOL, params, len(params), byte_data)
        else:
            txdata = [tool_type]
            return self.set_nu8(XCONF.UxbusReg.SET_COLLIS_TOOL, txdata, 1)

    def set_simulation_robot(self, on_off):
        txdata = [int(on_off)]
        return self.set_nu8(XCONF.UxbusReg.SET_SIMULATION_ROBOT, txdata, 1)

    def get_power_board_version(self):
        return self.get_nu8(XCONF.UxbusReg.GET_PWR_VERSION, 3)

    def vc_set_jointv(self, jnt_v, jnt_sync):
        return self.set_nfp32_with_bytes(XCONF.UxbusReg.VC_SET_JOINTV, jnt_v, 7, bytes([jnt_sync]))

    def vc_set_linev(self, line_v, coord):
        return self.set_nfp32_with_bytes(XCONF.UxbusReg.VC_SET_CARTV, line_v, 6, bytes([coord]))

    @lock_require
    def set_impedance(self, coord, c_axis, M, K, B):
        txdata = bytes([coord])
        txdata += bytes(c_axis)
        txdata += convert.fp32s_to_bytes(M, 6)
        txdata += convert.fp32s_to_bytes(K, 6)
        txdata += convert.fp32s_to_bytes(B, 6)
        ret = self.send_xbus(XCONF.UxbusReg.IMPEDANCE_CONFIG, txdata, 79)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP]
        return self.send_pend(XCONF.UxbusReg.IMPEDANCE_CONFIG, 0, self._SET_TIMEOUT)
    
    @lock_require
    def set_impedance_mbk(self, M, K, B):
        txdata = convert.fp32s_to_bytes(M, 6)
        txdata += convert.fp32s_to_bytes(K, 6)
        txdata += convert.fp32s_to_bytes(B, 6)
        ret = self.send_xbus(XCONF.UxbusReg.IMPEDANCE_CTRL_MBK, txdata, 72)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP]
        return self.send_pend(XCONF.UxbusReg.IMPEDANCE_CTRL_MBK, 0, self._SET_TIMEOUT)

    @lock_require
    def set_impedance_config(self, coord, c_axis):
        txdata = bytes([coord])
        txdata += bytes(c_axis)
        ret = self.send_xbus(XCONF.UxbusReg.IMPEDANCE_CTRL_CONFIG, txdata, 7)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP]
        return self.send_pend(XCONF.UxbusReg.IMPEDANCE_CTRL_CONFIG, 0, self._SET_TIMEOUT)

    @lock_require
    def config_force_control(self, coord, c_axis, f_ref, limits):
        txdata = bytes([coord])
        txdata += bytes(c_axis)
        txdata += convert.fp32s_to_bytes(f_ref, 6)
        txdata += convert.fp32s_to_bytes(limits, 6)
        ret = self.send_xbus(XCONF.UxbusReg.FORCE_CTRL_CONFIG, txdata, 55)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP]
        return self.send_pend(XCONF.UxbusReg.FORCE_CTRL_CONFIG, 0, self._SET_TIMEOUT)

    @lock_require
    def set_force_control_pid(self, kp, ki, kd, xe_limit):
        txdata = convert.fp32s_to_bytes(kp, 6)
        txdata += convert.fp32s_to_bytes(ki, 6)
        txdata += convert.fp32s_to_bytes(kd, 6)
        txdata += convert.fp32s_to_bytes(xe_limit, 6)
        ret = self.send_xbus(XCONF.UxbusReg.FORCE_CTRL_PID, txdata, 96)
        if ret != 0:
            return [XCONF.UxbusState.ERR_NOTTCP]
        return self.send_pend(XCONF.UxbusReg.FORCE_CTRL_PID, 0, self._SET_TIMEOUT)

    def ft_sensor_set_zero(self):
        return self.set_nu8(XCONF.UxbusReg.FTSENSOR_SET_ZERO, 0, 0)

    def ft_sensor_iden_load(self):
        return self.get_nfp32(XCONF.UxbusReg.FTSENSOR_IDEN_LOAD, 10, timeout=500)

    def ft_sensor_cali_load(self, iden_result_list):
        return self.set_nfp32(XCONF.UxbusReg.FTSENSOR_CALI_LOAD_OFFSET, iden_result_list, 10)

    def ft_sensor_enable(self, on_off):
        txdata = [on_off]
        return self.set_nu8(XCONF.UxbusReg.FTSENSOR_ENABLE, txdata, 1)

    def ft_sensor_app_set(self, app_code):
        txdata = [app_code]
        return self.set_get_nu8(XCONF.UxbusReg.FTSENSOR_SET_APP, txdata, 1, 1)

    def ft_sensor_app_get(self):
        return self.get_nu8(XCONF.UxbusReg.FTSENSOR_GET_APP, 1)

    def get_exe_ft(self):
        return self.get_nfp32(XCONF.UxbusReg.GET_EXE_FT, 6)

    def cali_tcp_pose(self, four_pnts):
        txdata = []
        for k in range(4):
            txdata += [four_pnts[k][i] for i in range(6)]
        return self.swop_nfp32(XCONF.UxbusReg.CALI_TCP_POSE, txdata, 24, 3)

    # default: mode: x+ then y+; trust_ind: trust x+ dir
    # @lock_require
    def cali_user_orient(self, three_pnts, mode=0, trust_ind=0):
        txdata = []
        for k in range(3):
            txdata += [three_pnts[k][i] for i in range(6)]
        byte_data = bytes([mode, trust_ind])
        rxn = 3
        ret = self.set_nfp32_with_bytes(XCONF.UxbusReg.CALI_WRLD_ORIENT, txdata, 18, byte_data, rxn * 4)
        data = [0] * (1 + rxn)
        data[0] = ret[0]
        data[1:rxn+1] = convert.bytes_to_fp32s(ret[1:rxn * 4 + 1], rxn)
        return data
        # fpdata = []
        # for k in range(3):
        #     fpdata += [three_pnts[k][i] for i in range(6)]
        # # return self.swop_nfp32(XCONF.UxbusReg.CALI_USER_ORIENT, fpdata, 18, 3)
        # hexdata = convert.fp32s_to_bytes(fpdata, 18)
        # hexdata += bytes([mode, trust_ind]) 
        # funcode = XCONF.UxbusReg.CALI_WRLD_ORIENT
        # ret = self.send_xbus(funcode, hexdata, 18 * 4 + 2)
        # rxn = 3; # to receive 3 fps as result 
        # if ret != 0:
        #     return [XCONF.UxbusState.ERR_NOTTCP] * (rxn + 1)
        # ret = self.send_pend(funcode, rxn * 4, self._GET_TIMEOUT)
        # data = [0] * (1 + rxn)
        # data[0] = ret[0]
        # data[1:rxn+1] = convert.bytes_to_fp32s(ret[1:rxn * 4 + 1], rxn)
        # return data

    def cali_tcp_orient(self, rpy_be, rpy_bt):
        txdata = [rpy_be[i] for i in range(3)]
        txdata += [rpy_bt[i] for i in range(3)]
        return self.swop_nfp32(XCONF.UxbusReg.CALI_TCP_ORIENT, txdata, 6, 3)

    def cali_user_pos(self, rpy_ub, pos_b_uorg):
        txdata = [rpy_ub[i] for i in range(3)]
        txdata += [pos_b_uorg[i] for i in range(3)]
        return self.swop_nfp32(XCONF.UxbusReg.CALI_WRLD_POSE, txdata, 6, 3) 