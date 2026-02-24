
# import dbus
# import dbus.service
# from dbus.mainloop.glib import DBusGMainLoop
# from gi.repository import GLib

from multiprocessing import Queue
# import os

def start_process(queue, dbusaddr, loop):

    # import os
    # os.environ["DBUS_SESSION_BUS_ADDRESS"] = dbusaddr

    # IMPORTANT: import AFTER env setup
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib
    import dbus


    # NOW create service
    BUS_NAME = 'com.kartik.peripheralshare'
    OBJECT_PATH = '/com/kartik/peripheralshare'
    INTERFACE_NAME = 'com.kartik.peripheralshare'

    class ShareDaemon(dbus.service.Object):
        """
        A D-Bus object that can be called by other applications.
        """
        def __init__(self, queue:Queue, dbusaddr):
            # Connect to the session bus and register the object path
            bus = dbus.SystemBus()

            self.q = queue
            bus_name_obj = dbus.service.BusName(BUS_NAME, bus=bus)
            dbus.service.Object.__init__(self, bus_name_obj, OBJECT_PATH)

        @dbus.service.method(
            dbus_interface=INTERFACE_NAME,
            in_signature='i'
        )
        def changedev(self, num) -> str:
            """
            Example method that takes a name and returns a greeting.
            """
            self.q.put(num)
            print(num)
            
    ShareDaemon(queue, dbusaddr)

    print("DBus service running")

    # loop.run()
    # 1. Set the GLib main loop as the default for dbus-python

# if __name__ == "__main__":
#     # 2. Instantiate the service object
# def start_process(queue, dbusaddr) :

#     DBusGMainLoop(set_as_default=True)

#     # Define a unique bus name and object path (conventional reverse-DNS format)

#     os.environ["DBUS_SESSION_BUS_ADDRESS"] = dbusaddr
#     eventserver = ShareDaemon(queue, dbusaddr)
#     print(f"Service {BUS_NAME} running at {OBJECT_PATH} on the Session Bus.")
#     print("Waiting for method calls...")

#     # 3. Run the GLib main loop to process D-Bus messages
#     loop = GLib.MainLoop()
#     loop.run()
