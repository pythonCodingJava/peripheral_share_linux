#!/usr/bin/python3

import dbus
import dbus.service
import dbus.mainloop.glib
import time
import evdev
from evdev import *
import logging
from logging import debug, info, warning, error
import os
import sys
from select import select
import pyudev
import re

logging.basicConfig(level=logging.DEBUG)

MUL = 2

class InputDevice():
    inputs = []

    @staticmethod
    def init():
        context = pyudev.Context()
        devs = context.list_devices(subsystem="input")
        InputDevice.monitor = pyudev.Monitor.from_netlink(context)
        InputDevice.monitor.filter_by(subsystem='input')
        InputDevice.monitor.start()
        for d in [*devs]:
            InputDevice.add_device(d)

    @staticmethod
    def add_device(dev):
        if dev.device_node == None or not re.match(".*/event\\d+", dev.device_node):
            return
        try:
            if "ID_INPUT_MOUSE" in dev.properties:
                print("detected mouse: " + dev.device_node)
                InputDevice.inputs.append(MouseInput('/dev/input/event7'))
                # InputDevice.inputs.append(MouseInput("/dev/input/event15"))
        except OSError:
            error("Failed to connect to %s", dev.device_node)

    @staticmethod
    def remove_device(dev):
        if dev.device_node == None or not re.match(".*/event\\d+", dev.device_node):
            return
        InputDevice.inputs = list(
            filter(lambda i: i.device_node != dev.device_node, InputDevice.inputs))
        print("Disconnected %s", dev)

    @staticmethod
    def set_leds_all(ledvalue):
        for dev in InputDevice.inputs:
            dev.set_leds(ledvalue)

    @staticmethod
    def grab(on):
        if on:
            for dev in InputDevice.inputs:
                dev.device.grab()
        else:
            for dev in InputDevice.inputs:
                dev.device.ungrab()

    def __init__(self, device_node):
        self.device_node = device_node
        self.device = evdev.InputDevice(device_node)
        self.device.grab()
        time.sleep(1)
        self.device.ungrab()
        info("Connected %s", self)

    def fileno(self):
        return self.device.fd

    def __str__(self):
        return "%s@%s (%s)" % (self.__class__.__name__, self.device_node, self.device.name)


class MouseInput(InputDevice):
    def __init__(self, device_node, grabbed, iface):
        super().__init__(device_node)
        self.state = [0, 0, 0, 0]
        self.x = 0
        self.y = 0
        self.z = 0

        self.grabbed = grabbed

        self.dtap = False
        self.currfing = 0

        self.dx = -1
        self.dy = -1
        self.dz = -1

        self.change = False
        self.last = 0
        # self.bus = dbus.SystemBus()
        # self.btkservice = self.bus.get_object(
        #     'org.kartik.btkbservice', '/org/kartik/btkbservice')
        # self.iface = dbus.Interface(self.btkservice, 'org.kartik.btkbservice')
        self.iface = iface
        self.mouse_delay = 10 / 1000
        self.mouse_speed = 1

        self.last_touch = -1

        self.held = False

    def send_current(self, ir):
        try:
            if self.grabbed.is_set() and not self.iface.send_mouse(0, bytes(ir)) :
                self.device.ungrab()
                # self.iface.listen()
        except OSError as err:
            error(err)

    def send_data(self):
        # diff = 20/1000
        speed = 1
        self.state[1] = min(127, max(-127, int(self.x * speed))) & 255
        self.state[2] = min(127, max(-127, int(self.y * speed))) & 255
        self.state[3] = min(127, max(-127, int(self.z))) & 255
        self.x = 0
        self.y = 0
        self.z = 0
        self.change = False
        self.send_current(self.state)

    def change_state(self, event):
        # if event.type == ecodes.EV_SYN:
        #     print(event)
        #     print(ecodes.EV_REL, ecodes.EV_SYN, ecodes.EV_KEY)
        
        if event.type == ecodes.EV_SYN:

            current = time.monotonic()
            diff = self.mouse_delay
            if current - self.last < diff and not self.change:
                return
            self.last = current
            # print(self.x,self.y,self.z)
            self.send_data()
        if event.type == ecodes.EV_KEY:
            # debug("Key event %s %d", ecodes.BTN[event.code], event.value)
            self.change = True
            if event.code == ecodes.BTN_TOOL_DOUBLETAP :
                if event.value == 1:
                    # print("Double tap detected")
                    self.dtap = True
                elif event.value == 0:
                    self.dx = -1
                    self.dy = -1
                    self.dz = -1
                    self.dtap = False

            if event.code == ecodes.BTN_TOUCH :
                if event.value == 0:
                    
                    if self.held:
                        self.held = False
                        button_no = ecodes.BTN_LEFT - 272
                        self.state[0] &= ~(1 << button_no)
                        self.send_data() 
                    elif time.time_ns() - self.last_touch < 100000000 and (self.x+self.y+self.z) == 0:
                        # print(self.x,self.y,self.z)
                        button_no = ecodes.BTN_LEFT - 272
                        self.state[0] |= 1 << button_no
                        self.send_data()
                        time.sleep(0.1)
                        self.state[0] &= ~(1 << button_no)
                        self.send_data()

                    self.dx = -1
                    self.dy = -1
                    self.dz = -1
                elif event.value == 1:
                    if time.time_ns() - self.last_touch < 300000000:
                        # print("held")
                        self.held = True
                        button_no = ecodes.BTN_LEFT - 272
                        self.state[0] |= 1 << button_no
                        self.send_data()

                    self.last_touch = time.time_ns()
            if event.code >= 272 and event.code <= 276 and event.value < 2:
                button_no = event.code - 272
                if event.value == 1:
                    self.state[0] |= 1 << button_no
                else:
                    
                    self.state[0] &= ~(1 << button_no)


        if event.type == ecodes.EV_ABS:
            if event.code == ecodes.ABS_MT_SLOT:
                self.currfing = event.value

            if not self.dtap :
                if event.code == ecodes.ABS_X:
                    self.x = event.value - (self.dx if self.dx != -1 else event.value)
                    self.x *= MUL
                    self.dx = event.value

                if event.code == ecodes.ABS_Y:
                    self.y = event.value - (self.dy if self.dy != -1 else event.value)
                    self.y *= MUL
                    self.dy = event.value

            elif event.code == ecodes.ABS_MT_POSITION_Y and self.currfing == 1:
                self.dx = -1
                self.dy = -1

                self.z = -1*(event.value - (self.dz if self.dz != -1 else event.value))
                # self.z *= MUL/2
                
                self.dz = event.value
                # print(self.dz)


        if event.type == ecodes.EV_REL:
            if event.code == ecodes.REL_X:
                self.x += event.value
            if event.code == ecodes.REL_Y:
                self.y += event.value
            if event.code == ecodes.REL_WHEEL:
                self.z -= 2*event.value

    def get_info(self):
        print("hello")

    def set_leds(self, ledvalue):
        pass




# if __name__ == "__main__":
    # main_loop()
