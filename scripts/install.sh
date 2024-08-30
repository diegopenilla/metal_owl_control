#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
METAL_OWL_CONTROL_DIR=$(realpath $SCRIPT_DIR/..)

#-------------------------------------------------------------------
echo ""
echo "Installing apt dependencies..."
echo "=============================="
sudo apt update
sudo apt install -y git pip

#-------------------------------------------------------------------
echo ""
echo "Installing WIFI Access Point..."
echo "=============================="
sudo apt-get install -y \
     libgtk-3-dev build-essential gcc g++ pkg-config make hostapd libqrencode-dev libpng-dev iptables
cd $METAL_OWL_CONTROL_DIR
git clone https://github.com/lakinduakash/linux-wifi-hotspot
cd linux-wifi-hotspot
make
sudo make install


sudo iw dev wlan0 interface add ap0 type __ap 
pkexec --user root create_ap ap0 wlan0 'OWLAP' 'changeme554433' --mkconfig /etc/create_ap.conf --freq-band 2.4

#Configure AP
#cp $METAL_OWL_CONTROL_DIR/scripts/services/create_ap.service /lib/systemd/system/create_ap.service
#cp $METAL_OWL_CONTROL_DIR/scripts/services/create_ap.conf /etc/create_ap.conf

#Enable Wifi AP Service
systemctl enable create_ap

#-------------------------------------------------------------------
echo ""
echo "Installing udev rules..."
echo "=============================="

# Define the udev rule for the Candlelight device
UDEV_RULE='ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="1d50", ATTRS{idProduct}=="606f", RUN+="/sbin/ip link set can0 up type can bitrate 500000"'

# Define the udev rules file path
UDEV_RULES_FILE='/etc/udev/rules.d/99-socketcan.rules'

# Check if the udev rules file exists
if [ ! -f "$UDEV_RULES_FILE" ]; then
    echo "Creating udev rules file: $UDEV_RULES_FILE"
    sudo touch "$UDEV_RULES_FILE"
fi

# Add the udev rule to the file if it doesn't already exist
if ! grep -Fxq "$UDEV_RULE" "$UDEV_RULES_FILE"; then
    echo "Adding udev rule to $UDEV_RULES_FILE"
    echo "$UDEV_RULE" | sudo tee -a "$UDEV_RULES_FILE" > /dev/null
else
    echo "Udev rule already exists in $UDEV_RULES_FILE"
fi

# Reload udev rules
echo "Reloading udev rules"
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "Udev rule installation complete."

#-------------------------------------------------------------------
echo ""
echo "Installing python dependencies..."
echo "=============================="
# create new virtual environment
cd $METAL_OWL_CONTROL_DIR
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt

#-------------------------------------------------------------------
echo ""
echo "Setup Owl Service..."
echo "=============================="

sudo cp $METAL_OWL_CONTROL_DIR/scripts/services/owl.service /etc/systemd/system/owl.service
sudo chmod +x $METAL_OWL_CONTROL_DIR/scripts/run_owl_server.sh
systemctl enable owl


#-------------------------------------------------------------------
echo ""
echo "Reboot to complete installation"
echo "=============================="


