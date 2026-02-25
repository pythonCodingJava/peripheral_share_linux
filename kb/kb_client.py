#!/usr/bin/python3
#
# Thanhle Bluetooth keyboard emulation service
# keyboard copy client.
# Reads local key events and forwards them to the btk_server DBUS service
#
import logging
import dbus
import time
from evdev import *
import kb.keymap  as keymap # used to map evdev input to hid keodes
# from notifier import show_menu

# Define a client to listen to local key events
class Keyboard():

    def __init__(self, grabbed, iface, disconnected, dev, queue):
        # the structure for a bt keyboard input report (size is 10 bytes)

        self.grabbed = grabbed
        self.disconnected = disconnected

        self.state = [
            0xA1,  # this is an input report
            0x01,  # Usage report = Keyboard
            # Bit array for Modifier keys
            [0,  # Right GUI - Windows Key
             0,  # Right ALT
             0,  # Right Shift
             0,  # Right Control
             0,  # Left GUI
             0,  # Left ALT
             0,  # Left Shift
             0],  # Left Control
            0x00,  # Vendor reserved
            0x00,  # rest is space for 6 keys
            0x00,
            0x00,
            0x00,
            0x00,
            0x00]
        
        self.consumer_control = [
            0xA1,
            0x03,
            0x00,
            0x00
        ]
        self.consume = False

        self.switch = False
        # print("setting up DBus Client")

        # self.bus = dbus.SystemBus()
        # self.btkservice = self.bus.get_object(
        #     'org.kartik.btkbservice', '/org/kartik/btkbservice')
        # self.iface = dbus.Interface(self.btkservice, 'org.kartik.btkbservice')
        self.iface = iface

        self.queue = queue
        # self.guirun = multiprocessing.Event()
        # self.gui = multiprocessing.Process(target=show_menu, args=("iPad",self.guirun,))
        # print("waiting for keyboard")
        # keep trying to key a keyboard
        # have_dev = False
        # while have_dev == False:
        try:
            # try and get a keyboard - should always be event0 as
            # we're only plugging one thing in
            # self.dev = InputDevice("/dev/input/event8")
            self.dev = InputDevice(dev)
            # time.sleep(1)
            # self.dev.grab()
            # self.grabbed.set()
        #     have_dev = True
        except OSError:
            print("Keyboard not found, waiting 3 seconds and retrying")
            time.sleep(3)
            print("found a keyboard")

    def change_state(self, event):
        if event.type != ecodes.EV_KEY or event.value >= 2:
            return 
                    
        self.rect =  time.time_ns()
        evdev_code = ecodes.KEY[event.code]

        if isinstance(evdev_code, list):
            return
        # print(evdev_code, event.value)
        modkey_element = keymap.modkey(evdev_code)


        if modkey_element > 0:
            if self.state[2][modkey_element] == 0:
                self.state[2][modkey_element] = 1
            else:
                self.state[2][modkey_element] = 0

            if self.state[2] == [0,0,0,0,0,0,0,0] and self.switch:
                # if not self.disconnected.is_set() :
                tograb = self.iface.currentconn == 0
                self.iface.currentconn += 1
                if len(self.iface.connections) <= self.iface.currentconn-1 :
                    self.iface.currentconn = 0
                    # self.guirun.set()
                    # self.gui.terminate()
                    self.queue.put(("destroy",))
                    
                elif tograb :
                    # self.guirun.clear()
                    # self.gui = multiprocessing.Process(target=show_menu, args=(list(self.iface.connections.values())[self.iface.currentconn-1]['name'],self.guirun,self.queue,))
                    # self.gui.start()
                    self.queue.put(("show",))
                    self.queue.put((list(self.iface.connections.values())[self.iface.currentconn-1]['name'], ))
                    self.grabbed.set()
                    self.dev.grab()
                else :
                    self.queue.put((list(self.iface.connections.values())[self.iface.currentconn-1]['name'], ))
                print(self.iface.currentconn)
                    
                self.switch = False
                

            if self.state[2] == [0,0,0,0,1,1,0,1]:
                print("Windows + Ctrl + Alt detected")
                self.switch = True
        else:
            # Get the keycode of the key
            hex_key = keymap.convert(ecodes.KEY[event.code])
            if ecodes.KEY[event.code] == "KEY_F3":
                # print("volume up")
                self.consumer_control[2] = 0xE9 if event.value == 1 else 0x00
                self.consume = True
                # self.iface.send_string(bytes([0xA1, 0x03, 0xE9, 0x00]))
                # time.sleep(0.03)
                # self.iface.send_string(bytes([0xA1, 0x03, 0x00, 0x00]))
            elif ecodes.KEY[event.code] == "KEY_F2":
                # print("volume down")
                self.consumer_control[2] = 0xEA if event.value == 1 else 0x00
                self.consume == True
            
            elif ecodes.KEY[event.code] == "KEY_F4":
                self.consumer_control[2] = 0xE2 if event.value == 1 else 0x00
                self.consume == True

            else :
            # Loop through elements 4 to 9 of the inport report structure
                for i in range(4, 10):
                    if self.state[i] == hex_key and event.value == 0:
                        # Code 0 so we need to depress it
                        self.state[i] = 0x00
                    elif self.state[i] == 0x00 and event.value == 1:
                        # if the current space if empty and the key is being pressed
                        self.state[i] = hex_key
                        break
        
        if self.grabbed.is_set():
            self.send_input()

    # poll for keyboard events
    def event_loop(self):
        for event in self.dev.read_loop():
            # if not self.grabbed:
            #     continue
            # only bother if we hit a key and its an up or down event
            if event.type == ecodes.EV_KEY and event.value < 2:
                self.change_state(event)
                if self.grabbed.is_set():
                    self.send_input()

    # forward keyboard events to the dbus service
    def send_input(self):
        if self.consume :
            if not self.iface.send_string(bytes(self.consumer_control)) :
                self.grabbed.clear()
                self.dev.ungrab()
            self.consume = False
            return
        
        bin_str = ""
        element = self.state[2]
        for bit in element:
            bin_str += str(bit)
        a = self.state
        # print(*a)
        try :
            if not self.iface.send_keys(int(bin_str, 2), self.state[4:10]) :
                self.grabbed.clear()
                self.dev.ungrab()
                # self.iface.listen()
        except dbus.DBusException as err:
            self.grabbed.clear()
            logging.warning("DBus error: %s", err)
        except OSError as e:
            logging.warning(e)
        # print(f'time taken : {(time.time_ns() - self.rect)/1000000} ms')

