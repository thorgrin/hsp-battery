# Bluetooth HSP Battery status reader

The goal of this project is to get battery status on headsets in Linux.

## Supported protocols
Current implementation uses BlueZ to get connection to HSP profile of a newly connected device.
It interprets only the `AT+IPHONEACCEV` command used by Apple.

The only problem is that it snatches the handling of the BT headset profile from pulseaudio. 
On the other hand, the pulseaudio does not do anything useful with it and does not seem to mind

## Unsupported protocols

* It should be possible to add support for `AT+CIND battchg` command on HSP protocol; 
however, I have no such device at my desposal.
* Another way to report battery status of headset is through AVRCP protocol, which is used in A2DP. 
The handling must be added to BlueZ, search for `avrcp_handle_ct_battery_status()`.
* Many devices support the GATT protocol. This should be supported by BlueZ as well as Upower.
