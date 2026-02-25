#!/usr/bin/python3
#
# Bluetooth keyboard/Mouse emulator DBUS Service
#

from __future__ import absolute_import, print_function
import multiprocessing
from optparse import OptionParser, make_option
import os
import sys
import uuid
import dbus
import dbus.service
import dbus.mainloop.glib
import time
import socket
# from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop
import logging
from logging import debug, info, warning, error
import bluetooth
from bluetooth import *
import threading

import subprocess

logging.basicConfig(level=logging.DEBUG)

# @todo fill your host mac here manually

class BTKbDevice():
    # change these constants
    MY_DEV_NAME = "Peripheral Share"

    # define some constants
    P_CTRL = 17  # Service port - must match port configured in SDP record
    P_INTR = 19  # Interrupt port - must match port configured in SDP record
    # dbus path of the bluez profile we will create
    # file path of the sdp record to load
    SDP_RECORD_PATH = sys.path[0] + "/server/sdp_record.xml"
    UUID = "00001124-0000-1000-8000-00805f9b34fb"

    

    def __init__(self):
        print("2. Setting up BT device")
        self.init_bt_device()
        self.init_bluez_profile()
        self.currentconn = 0
        self.connections = {}
        self.threads = []

    # configure the bluetooth hardware device
    def init_bt_device(self):
        print("3. Configuring Device name " + BTKbDevice.MY_DEV_NAME)
        # set the device class to a keybord and set the name
        subprocess.run('rfkill unblock bluetooth'.split(" "))
        os.system("hciconfig hci0 up")
        os.system(f"hciconfig hci0 name '{BTKbDevice.MY_DEV_NAME}'")
        # make the device discoverable
        os.system("hciconfig hci0 piscan")

    # set up a bluez profile to advertise device capabilities from a loaded service record
    def init_bluez_profile(self):
        print("4. Configuring Bluez Profile")
        # setup profile options
        service_record = self.read_sdp_service_record()
        opts = {
            "AutoConnect": True,
            "ServiceRecord": service_record
        }
        # retrieve a proxy for the bluez profile interface
        bus = dbus.SystemBus()
        manager = dbus.Interface(bus.get_object(
            "org.bluez", "/org/bluez"), "org.bluez.ProfileManager1")
        manager.RegisterProfile("/org/bluez/hci0", BTKbDevice.UUID, opts)
        #print("6. Profile registered ")
        os.system("hciconfig hci0 class 0x002540")

    # read and return an sdp record from a file
    def read_sdp_service_record(self):
        print("5. Reading service record")
        try:
            fh = open(BTKbDevice.SDP_RECORD_PATH, "r")
        except:
            sys.exit("Could not open the sdp record. Exiting...")
        return fh.read()

    def setup_socket(self):
        self.scontrol = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)  # BluetoothSocket(L2CAP)
        self.sinterrupt = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)  # BluetoothSocket(L2CAP)
        self.scontrol.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sinterrupt.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.scontrol.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.sinterrupt.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)


        self.scontrol.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65535)
        self.scontrol.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65535)
        self.sinterrupt.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65535)
        self.sinterrupt.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65535)
        
        # bind these sockets to a port - port zero to select next available
        self.scontrol.bind((socket.BDADDR_ANY, self.P_CTRL))
        self.sinterrupt.bind((socket.BDADDR_ANY, self.P_INTR))



    # listen for incoming client connections
    def listen(self):

        self.setup_socket()

        # Start listening on the server sockets
        
        # os.system(f"bluetoothctl disconnect {TARGET_ADDRESS}")
        print("\033[0;33m7. Waiting for connections\033[0m")
        self.scontrol.listen(5)
        self.sinterrupt.listen(5)
        
        while True : 
            self.ccontrol,cinfo = self.scontrol.accept()
            # print(cinfo)
            t = threading.Thread(target=self.control_thread, args=(self.ccontrol,))
            t.start()
            
            device_name = ""
            try:
                device_name = bluetooth.lookup_name(cinfo[0])
                if device_name:
                    print(f"Device name: {device_name}")
                else:
                    print("Could not determine device name (returned None)")
            except bluetooth.BluetoothError as e:
                print(f"Error looking up device name: {e}")

            print (
                "\033[0;32mGot a connection on the control channel from %s \033[0m" % cinfo[0])

            self.cinterrupt, cinfo = self.sinterrupt.accept()
            print (
                "\033[0;32mGot a connection on the interrupt channel from %s \033[0m" % cinfo[0])

            t2 = threading.Thread(target=self.interrupt_thread, args=(self.cinterrupt,))
            t2.start()

            # t3 = threading.Thread(target=self.interrupt_keepalive_thread, args=(self.cinterrupt,))
            # t3.start()
            self.connections.update({
                cinfo[0]:{
                    "name":device_name,
                    "control":self.ccontrol,
                    "interrupt":self.cinterrupt,
                    "time":time.time_ns()
                }
            })

            print(len(self.connections))

        # return cinfo[0]
    
    def interrupt_keepalive_thread(self, sock:socket.socket):
        try:
            while True:
                print("Sending keepalive")
                sock.send(bytes([ 0xA1, 1, 0, 0, 0, 0, 0, 0, 0, 0 ]))
                time.sleep(5)
        except Exception as e :
            print(e)

    def interrupt_thread(self, sock:socket.socket):
        print("Starting interrupt thread")
        try:
            while True:
                
                data = sock.recv(1024)
                if not data:
                    break
                print(data)
                # optionally print or ignore
        except Exception as e:
            print("Interrupt socket error:", e)

    def control_thread(self, sock):
        print("Control thread started")
        try :
            while True:
                try :
                    data = sock.recv(1024)
                    if not data:
                        break
                    print(data)
                    header = data[0]
                    msg_type = header & 0xF0
                    if msg_type == 0x70:  # SET_IDLE
                        sock.send(b'\x00')  # handshake success
                    elif msg_type == 0x90:  # SET_PROTOCOL
                        sock.send(b'\x00')
                    elif msg_type == 0x40:  # GET_REPORT
                        neutral = b'\xA1\x01\x00\x00\x00\x00\x00\x00\x00'
                        sock.send(neutral)
                    else:
                        # unknown but acknowledge
                        sock.send(b'\x00')
                except socket.timeout as e :
                   continue
        except Exception as e :
            print("Control thread error : ", e)
        # if data[0] == 0x02:   # SET_IDLE
        #     control_sock.send(b'\x00')

        # elif data[0] == 0x01: # GET_REPORT
        #     control_sock.send(dummy_report)


    # send a string to the bluetooth host machine
    def send_string(self, message):

        if len(self.connections) <= self.currentconn-1:
            self.currentconn = 0
        if self.currentconn == 0:
            return False
            
        try:
            # if len(self.connections) == 0:
            #     return False
            
            mac = list(self.connections.keys())[self.currentconn-1]
            self.connections[mac]['interrupt'].send(bytes(message))

            # dead = []
            # for e in self.connections:
            #     try :
            #         self.connections[e]['interrupt'].send(bytes(message))
            #     except OSError:
            #         dead.append(e)
            
            # for m in dead:
            #     self.connections.pop(m)
            return True
        except OSError as err:
            print("sending data failed")
            # self.connections.pop(list(self.connections.keys())[self.currentconn-1])
            # self.currentconn = 0
            error(err)
            return False
            # self.listen()

    def get_mac(self):
        if self.cinfo is not None :
            return self.cinfo[0]
        else :
            return ""
        
    def send_keys(self, modifier_byte, keys):
        # print("Get send_keys request through dbus")
        # print("key msg: ", keys)
        state = [ 0xA1, 1, 0, 0, 0, 0, 0, 0, 0, 0 ]
        state[2] = int(modifier_byte)
        count = 4
        for key_code in keys:
            if(count < 10):
                state[count] = int(key_code)
            count += 1
        return self.send_string(state)

    

    def send_mouse(self, modifier_byte, keys):
        #print("sending mouse through dbus")
        state = [0xA1, 2, 0, 0, 0, 0]
        count = 2
        for key_code in keys:
            if(count < 6):
                state[count] = int(key_code)
            count += 1
        return self.send_string(state)

