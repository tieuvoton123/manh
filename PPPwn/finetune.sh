#!/bin/bash

#disable some service to reducing boot time, around 6-7 sec.
#target on armbian devices.

#uncomment to check boot time.
#systemd-analyze time

#uncomment to check service time.
#systemd-analyze blame

echo -e ''
echo -e '\033[37mThis is script for fine tuning armbian os, press crtl-c to exit\033[0m'

while true; do
read -p "$(printf '\r\n\r\n\033[37mDo you want to run the script\r\n\r\n\033[37m(Y|N)?: \033[0m')" finetuning
case $finetuning in
[Yy]* ) 
echo -e '\033[32mRunning the script\033[0m'
break;;
[Nn]* ) 
echo -e '\033[33mAbort\033[0m'
exit 0;;
* ) echo -e '\033[31mPlease answer Y or N\033[0m';;
esac
done

#disable armbian-ramlog, gain 2 sec.
sudo mv /etc/default/armbian-ramlog /etc/default/armbian-ramlog.bak
sudo mv /etc/cron.d/armbian-truncate-logs /etc/cron.d/armbian-truncate-logs.bak
sudo mv /etc/cron.daily/armbian-ram-logging /etc/cron.daily/armbian-ram-logging.bak
sudo mv /etc/systemd/system/sysinit.target.wants/armbian-ramlog.service /etc/systemd/system/sysinit.target.wants/armbian-ramlog.service.bak

#disable armbian-zram-config.service, gain 0.1 sec.
sudo mv /etc/default/armbian-zram-config /etc/default/armbian-zram-config.bak
sudo mv /etc/systemd/system/sysinit.target.wants/armbian-zram-config.service /etc/systemd/system/sysinit.target.wants/armbian-zram-config.service.bak

#disable armbian-hardware-monitor.service, gain 1.1 sec.
sudo mv /etc/systemd/system/basic.target.wants/armbian-hardware-monitor.service /etc/systemd/system/basic.target.wants/armbian-hardware-monitor.service.bak

#disable armbian-hardware-optimize.service, gain 0.1 sec.
sudo mv /etc/systemd/system/basic.target.wants/armbian-hardware-optimize.service /etc/systemd/system/basic.target.wants/armbian-hardware-optimize.service.bak

#disable NetworkManager-wait-online.service, gain 2.2 sec.
sudo mv /etc/systemd/system/network-online.target.wants/NetworkManager-wait-online.service /etc/systemd/system/network-online.target.wants/NetworkManager-wait-online.service.bak

#disable bluetooth
sudo mv /usr/lib/systemd/user/bluetooth.target /usr/lib/systemd/user/bluetooth.target.bak

#uncomment to check freq and governor.
#cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_frequencies
#cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governor

#Modify cpufrequtils, edit value depend on your cpu.
echo 'ENABLE=true
MIN_SPEED=1000000
MAX_SPEED=1510000
GOVERNOR=performance' | sudo tee /etc/default/cpufrequtils

#Restore default network interfaces
#sudo cp /etc/network/interfaces.default /etc/network/interfaces

#edit /etc/passwd and remove the x in field password (second field in first line).

echo -e '\033[37mInstall complete\033[0m'