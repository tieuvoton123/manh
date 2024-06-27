#!/bin/bash

if [ -f /boot/firmware/PPPwn/config.sh ]; then
source /boot/firmware/PPPwn/config.sh
fi
if [ -f /boot/firmware/PPPwn/pconfig.sh ]; then
source /boot/firmware/PPPwn/pconfig.sh
fi

#[7.00, 7.01, 7.02] [7.50, 7.51, 7.55] [8.00, 8.01, 8.03] [8.50, 8.52] 9.00 [9.03, 9.04] [9.50, 9.51, 9.60] [10.00, 10.01] [10.50, 10.70, 10.71] 11.00

if [ -z $INTERFACE ]; then INTERFACE="eth0"; fi
if [ -z $FIRMWAREVERSION ]; then FIRMWAREVERSION="11.00"; fi
if [ -z $USBETHERNET ]; then USBETHERNET=false; fi
if [ -z $USEIPV6 ]; then USEIPV6=false; fi
if [ -z $TIMEOUT ]; then TIMEOUT="5m"; fi

if [ -z $XFWAP ]; then XFWAP="1"; fi
if [ -z $XFGD ]; then XFGD="4"; fi
if [ -z $XFBS ]; then XFBS="0"; fi
if [ -z $XFNWB ]; then XFNWB=false; fi
if [ $USEIPV6 = false ] ; then
XFIP="fe80::4141:4141:4141:4141"
else
XFIP="fe80::9f9f:41ff:9f9f:41ff"
fi
if [ $XFNWB = true ] ; then
XFNW="--no-wait-padi"
else
XFNW=""
fi

if [ $USBETHERNET = true ] ; then
	echo '1-1' | sudo tee /sys/bus/usb/drivers/usb/unbind
	echo '1-1' | sudo tee /sys/bus/usb/drivers/usb/bind
fi

PITYP=$(tr -d '\0' </proc/device-tree/model) 
if [[ $PITYP == *"Raspberry Pi 2"* ]] ;then
coproc read -t 15 && wait "$!" || true
CPPBIN="pppwn7"
elif [[ $PITYP == *"Raspberry Pi 3"* ]] ;then
coproc read -t 10 && wait "$!" || true
CPPBIN="pppwn64"
elif [[ $PITYP == *"Raspberry Pi 4"* ]] ;then
coproc read -t 5 && wait "$!" || true
CPPBIN="pppwn64"
elif [[ $PITYP == *"Raspberry Pi 5"* ]] ;then
coproc read -t 5 && wait "$!" || true
CPPBIN="pppwn64"
elif [[ $PITYP == *"Raspberry Pi Zero 2"* ]] ;then
coproc read -t 8 && wait "$!" || true
CPPBIN="pppwn64"
elif [[ $PITYP == *"Raspberry Pi Zero"* ]] ;then
coproc read -t 10 && wait "$!" || true
CPPBIN="pppwn11"
elif [[ $PITYP == *"Raspberry Pi"* ]] ;then
coproc read -t 15 && wait "$!" || true
CPPBIN="pppwn11"
else
coproc read -t 5 && wait "$!" || true
CPPBIN="pppwn64"
fi
arch=$(getconf LONG_BIT)
if [ $arch -eq 32 ] && [ $CPPBIN = "pppwn64" ] && [[ ! $PITYP == *"Raspberry Pi 4"* ]] && [[ ! $PITYP == *"Raspberry Pi 5"* ]] ; then
CPPBIN="pppwn7"
fi

echo -e "\n\n\033[36m 
  _    _               _____   _  __    _____     _____   _  _       __   __        ___     ___  
 | |  | |     /\      / ____| | |/ /   |  __ \   / ____| | || |     /_ | /_ |      / _ \   / _ \ 
 | |__| |    /  \    | |      | ' /    | |__) | | (___   | || |_     | |  | |     | | | | | | | |
 |  __  |   / /\ \   | |      |  <     |  ___/   \___ \  |__   _|    | |  | |     | | | | | | | |
 | |  | |  / ____ \  | |____  | . \    | |       ____) |    | |      | |  | |  _  | |_| | | |_| |
 |_|  |_| /_/    \_\  \_____| |_|\_\   |_|      |_____/     |_|      |_|  |_| (_)  \___/   \___/ 
                                                                                                 
                                                                                                 
\033[0m
\n\033[33mhttps://github.com/TheOfficialFloW/PPPwn\033[0m\n" | sudo tee /dev/tty1

echo -e "\033[37mHack by      : Chepgameps4.com\033[0m" | sudo tee /dev/tty1
echo -e "\033[37mSdt   : 0987929209\033[0m" | sudo tee /dev/tty1

sudo systemctl stop pppoe
if [ $USBETHERNET = true ] ; then
	echo '1-1' | sudo tee /sys/bus/usb/drivers/usb/unbind
	coproc read -t 1 && wait "$!" || true
	echo '1-1' | sudo tee /sys/bus/usb/drivers/usb/bind
	coproc read -t 4 && wait "$!" || true
	sudo ip link set $INTERFACE up
else
	sudo ip link set $INTERFACE down
	coproc read -t 4 && wait "$!" || true
	sudo ip link set $INTERFACE up
fi

echo -e "\n\033[36m$PITYP\033[92m\nFirmware:\033[93m $FIRMWAREVERSION\033[92m\nInterface:\033[93m $INTERFACE\033[0m" | sudo tee /dev/tty1

echo -e "\033[92mPPPwn:\033[93m C++ $CPPBIN \033[0m" | sudo tee /dev/tty1

echo -e "\033[95mDANG HACK NHE....\033[0m" | sudo tee /dev/tty1

while [ true ]
do
while read -r stdo ; 
do 
if [[ $stdo  == "[+] Done!" ]] ;then
coproc read -t 6 && wait "$!" || true
sudo poweroff
fi
done < <(timeout $TIMEOUT sudo /boot/firmware/PPPwn/$CPPBIN --interface "$INTERFACE" --fw "${FIRMWAREVERSION//.}" --ipv $XFIP --wait-after-pin $XFWAP --groom-delay $XFGD --buffer-size $XFBS $XFNW)
sudo ip link set $INTERFACE down
coproc read -t 3 && wait "$!" || true
sudo ip link set $INTERFACE up
done