
# Bluetooth HID Share (Linux)

Share your keyboard and mouse with nearby devices over Bluetooth.  
This project turns a Linux machine into a Bluetooth HID device, allowing other computers, tablets, or phones to use it as a wireless keyboard and mouse.

---

## Features

- Share keyboard and mouse over Bluetooth
- Works with phones, tablets, laptops, and TVs
- Fast device switching via hotkey
- Python implementation
- No additional hardware required
- Designed as a foundation for a larger open-source peripheral sharing ecosystem

---

## Concept

Many proprietary ecosystems (a certain fruit company) allow a single keyboard and mouse to seamlessly control multiple devices.  
This project aims to provide an open implementation of that idea.

Input flow:

Physical Keyboard / Mouse  
→ Linux input subsystem  
→ Python HID encoder  
→ Bluetooth HID device  
→ Target device

The Linux host advertises itself as a Bluetooth keyboard and mouse and forwards local input events as HID reports.

---

## Platform Support

### Linux (Supported)

Linux allows user applications to register custom Bluetooth profiles using BlueZ and expose themselves as HID devices.

### Windows (Not Supported)

Windows does not allow user-space applications to present themselves as Bluetooth HID peripherals. This restriction is architectural and enforced by the operating system's Bluetooth driver model.

For Windows, you can run this program on a raspberry pi with the windows machine as a client and connect other devices as client as well.

---

## Requirements

- Linux system
- BlueZ Bluetooth stack
- Python 3.10+
- Root privileges

Setup your device:

```bash
sudo ./setup.sh
```

---

## Usage

Run the application with root privileges:

```bash
sudo python3 main.py
```

On startup the program will:

- Initialize the Bluetooth HID service
- Advertise itself as a keyboard and mouse
- Wait for incoming pairing requests
- Begin forwarding keyboard and mouse events

---

## Pairing a Device

1. Open Bluetooth settings on the target device.
2. Start scanning for new devices.
3. Select the advertised device name (default = "Peripheral Share", can be changed in server/btk_server.py).
4. Complete pairing.

---

## Switching Between Devices

Press:

```
Ctrl + Win + Alt
```

Each key combination cycles control to the next paired device.

Only one device receives input at a time.

---

## Stopping the Program

Terminate using:

```bash
Ctrl + C
```

The Bluetooth service will stop advertising and release HID control.

---

## Notes

- Root privileges are required to access input devices and Bluetooth HID interfaces.
- Ensure the BlueZ input plugin is disabled before running.
- Existing Bluetooth keyboards or mice connected to the Linux host may not function while the program is active.