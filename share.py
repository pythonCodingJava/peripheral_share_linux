from select import select
import threading
import time
import kb.kb_client
import mouse.mouse_client
from multiprocessing import Process, Event, Queue
import signal 
import dbus
import traceback
import logging
from logging import warning
# import notification
import pyudev
import re
# from websocket import warning
import notifier
import dbus as dbb
import asyncio
import dbus_service as db
from mouse.mouse_client import InputDevice
from evdev import ecodes

import server.btk_server as server
import os

from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

DBusGMainLoop(set_as_default=True)
# Create mainloop FIRST
dbusloop = GLib.MainLoop()

dbus_addr = os.environ["DBUS_SESSION_BUS_ADDRESS"]

logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# kb = None
mouse_process = None

run = Event()
run.clear()

def handle_interrupt(signum, frame):
    global t
    run.set()
    logging.info("Interrupt received, shutting down...")
    exit(0)


    # def event_loop(kb):

grabbed = asyncio.Event()
grabbed.clear()

async def mouse_worker(grabbed, devnode, run, server, disconnected):
    try:
        mse = mouse.mouse_client.MouseInput(devnode, grabbed, server)
        while not run.is_set():
            # desctiptors = [*InputDevice.inputs, InputDevice.monitor]
            # r = select(desctiptors, [], [])
                async for event in mse.device.async_read_loop():
                    try:
                        if disconnected.is_set():
                            grabbed.clear()

                        if grabbed.is_set():
                            mse.device.grab()
                        else:
                            mse.dx = -1
                            mse.dy = -1
                            mse.dz = -1
                            mse.device.ungrab()
                    except OSError as err:
                        pass
                    
                    if grabbed.is_set():
                        mse.change_state(event)
    except OSError as err:
        traceback.print_exc()
        logging.warning("overall err: %s", err)
    except Exception as e :
        traceback.print_exc()

async def keyboard_worker(grabbed, mac, run, server, disconnected, log_queue):
    # print("Setting up keyboard worker")
    try:
        kbrd = kb.kb_client.Keyboard(grabbed, server, disconnected, mac, log_queue)
        while not run.is_set():
                async for event in kbrd.dev.async_read_loop():
                    if not grabbed.is_set() :
                        try :
                            kbrd.dev.ungrab()
                        except OSError :
                            pass
                    else :
                        try :
                            kbrd.dev.grab()
                        except OSError :
                            pass

                    # if not kbrd.grabbed:
                    #     continue
                    # only bother if we hit a key and its an up or down event
                    if event.type == ecodes.EV_KEY and event.value < 2:
                        kbrd.change_state(event)
                        if grabbed.is_set():
                            kbrd.send_input()
    except OSError as err:
        traceback.print_exc()
        logging.warning("overall err: %s", err)
    except Exception as e:
        traceback.print_exc()    # warning(err)


# MAC = "BC:BB:58:71:E0:A9"
ADAPTER = "hci0"
# if __name__ == "__main__":
server_obj = None
task = {}

disconnected = Event()

t = None

async def main():
    signal.signal(signal.SIGINT, handle_interrupt)

    loop = asyncio.get_running_loop()

    # print("Setting up keyboard")

    server_obj = server.BTKbDevice()
    t = threading.Thread(target=server_obj.listen)
    # server_obj.listen()
    t.start()

    queue = Queue() 
    guirun = Event()
    
    guip = Process(target=notifier.main_loop, args=(guirun, queue, ))
    guip.start()

    dbq = Queue()
    # dbus = Process(target=db.start_process, args=(dbq,dbus_addr,dbusloop))
    # dbus.start()

    async def checker(run, iface, disconnected, queue):
        device_props = {}

        bus = dbb.SystemBus()


        # print("checking disconnections...")
        while not run.is_set():
            # print("checking disconnections...")
            discon = []
            if iface.currentconn == 0 :
                grabbed.clear()
            # else :
                # grabbed.set()
            for MAC in iface.connections :
                try :
                    if not MAC in device_props.keys() :

                        device_path = f"/org/bluez/{ADAPTER}/dev_{MAC.replace(':','_')}"
                        
                        device_props[MAC] = dbb.Interface(
                            bus.get_object("org.bluez", device_path),
                            "org.freedesktop.DBus.Properties"
                        )

                    connected = device_props[MAC].Get("org.bluez.Device1", "Connected")
                    # print(connected)
                    if not bool(connected) :
                        
                        print(f"{iface.connections[MAC]['name']} Disconnected after {(time.time_ns() - iface.connections[MAC]['time'])/1000000000} seconds")
                        discon.append(MAC)
                except Exception as e :
                    print(e)
                    discon.append(MAC)
                    

            for mac in discon :
                iface.connections.pop(mac)
            if len(discon) > 0 :
                if len(iface.connections) <= iface.currentconn-1 :
                    iface.currentconn = 0
                    queue.put(("destroy",))
                else :
                    queue.put((list(iface.connections.values())[iface.currentconn-1]['name'], ))

            if len(iface.connections) == 0:
                # print("No devices connected..")
                disconnected.set()
                await asyncio.sleep(5)
            else :
                # print("devices connected..")
                disconnected.clear()

            await asyncio.sleep(0.2)

    # p = 
    # p.start()

    touchpads = []
    keyboards = [] 

    context = pyudev.Context()
    devs = context.list_devices(subsystem="input")
    

    def usb_listener(d, loop):
        print(d.action)
        if d.action == "remove" or d.device_node == None or not re.match(".*/event\\d+", d.device_node):
            return
        
        if "ID_INPUT_MOUSE" in d.properties:
            # touchpads.append(d.device_node)
            
            future = asyncio.run_coroutine_threadsafe(mouse_worker(grabbed, d.device_node, run, server_obj, disconnected), loop)
            task[d.device_node] = future
            future.add_done_callback(lambda x: task.pop(d.device_node))
            print("Mouse detected: %s", d.device_node)

        if "ID_INPUT_TOUCHPAD" in d.properties:
            # touchpads.append(d.device_node)

            future = asyncio.run_coroutine_threadsafe(mouse_worker(grabbed, d.device_node, run, server_obj, disconnected), loop)
            task[d.device_node] = future
            future.add_done_callback(lambda x: task.pop(d.device_node))
            print("Touchpad detected: %s", d.device_node)
        
        if "ID_INPUT_KEYBOARD" in d.properties:
            # keyboards.append(d.device_node)

            future = asyncio.run_coroutine_threadsafe(keyboard_worker(grabbed, d.device_node, run, server_obj, disconnected,queue), loop)
            task[d.device_node] = future
            future.add_done_callback(lambda x: task.pop(d.device_node))
            print("keyboard detected: %s", d.device_node)



    for d in [*devs]:
        # print(d)
        if d.device_node == None or not re.match(".*/event\\d+", d.device_node):
            continue
        
        if "ID_INPUT_MOUSE" in d.properties:
            touchpads.append(d.device_node)
            print("Mouse detected: %s", d.device_node)

        if "ID_INPUT_TOUCHPAD" in d.properties:
            touchpads.append(d.device_node)
            print("Touchpad detected: %s", d.device_node)
        

        if "ID_INPUT_KEYBOARD" in d.properties:
            keyboards.append(d.device_node)
            print("keyboard detected: %s", d.device_node)




    task = {
        "checker" : asyncio.create_task(checker(run,server_obj,disconnected, queue)),
        # asyncio.create_task(mouse_worker(grabbed, run)),
        # asyncio.create_task(keyboard_worker(grabbed, run, server_obj, disconnected)),
    }

    # t = threading.Thread(target=usb_listener, args=(task, context,))
    # t.start()

    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='input')
    observer = pyudev.MonitorObserver(monitor, callback=lambda x: usb_listener(x,loop))
    
    # 3. Start the observer thread
    observer.start()
    print("Monitoring started. Plug/unplug a USB device to see events. Press Ctrl+C to stop.")
    

    for tp in touchpads:
        # print("Starting mouse worker for %s", tp)
        tas = asyncio.create_task(mouse_worker(grabbed, tp, run, server_obj, disconnected))
        task.update({tp:tas})
        tas.add_done_callback(lambda x: task.pop(tp))


    for kbrd in keyboards:
        # print("Starting mouse worker for %s", kbrd)
        # task.update({kbrd:asyncio.create_task()})
        tas = asyncio.create_task(keyboard_worker(grabbed, kbrd, run, server_obj, disconnected,queue))
        task.update({kbrd:tas})
        tas.add_done_callback(lambda x: task.pop(kbrd))

    db.start_process(dbq,dbus_addr, dbusloop)

    context = GLib.MainContext.default()
    while task :
        try : 
            context.iteration(False)
            obj = dbq.get_nowait()
            if obj == 0 :
                server_obj.currentconn = 0
                queue.put(("destroy",))
            else :
                server_obj.currentconn += 1
                
                if len(server_obj.connections) <= server_obj.currentconn-1 :
                    server_obj.currentconn = 0
                    queue.put(("destroy",))
                else :
                    queue.put(("show",))
                    queue.put((list(server_obj.connections.values())[server_obj.currentconn-1]['name'], ))
                    grabbed.set()
            print(obj)
        except Exception :
            pass
        await asyncio.sleep(0.1)
    await asyncio.gather(*task.items())

if __name__ == "__main__":
    asyncio.run(main())