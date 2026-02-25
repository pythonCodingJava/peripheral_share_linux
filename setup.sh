#!/bin/bash
sudo apt-get update -y
sudo apt-get install -y --ignore-missing git tmux bluez bluez-tools bluez-firmware
sudo apt-get install -y --ignore-missing python3 python3-dev python3-pip

sudo apt-get install -y libbluetooth-dev
sudo PIP_BREAK_SYSTEM_PACKAGES=1 pip3 install git+https://github.com/pybluez/pybluez.git#egg=pybluez

python -m venv venv
./venv/bin/pip install -r requirements.txt

sudo sed -i '/^ExecStart=/ s/$/ --noplugin=input/' /lib/systemd/system/bluetooth.service
sudo systemctl daemon-reload
sudo systemctl restart bluetooth.service

source venv/bin/activate
