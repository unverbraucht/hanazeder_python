# Hanazeder
This is a Python library and accompanying CLI utility for reading sensor values
from Hanazeder FP heating pumps.

Based on the work done by Thomas Binders serial_hlc20 (https://github.com/binderth/serial_hlc20) and 
Benedikt Merz research in his blog at (https://benedikt-merz.de/Blog/?p=157) - both very much appreciated!


# DISCLAIMER
With this connection, you could change all the values of your Hanazeder controller, which could result to a non-functional heating! Be careful, what parameter you're about to write. If you're only using read, you're safe!
I don't take responsibilities for any damage or mis-interpretation caused by the python script. Use it at your own risk!
## Hardware requirements
This python script opens a serial connection to the hanazeder FP10 home automation controller (http://hanazeder.at/page/building-automation) and reads out the values of the programmed modules (e.g. temperature sensors, valve statusses, ...).
1. hanazeder FP system (so far only tested with FP10)
2. serial connection (either direct or via USB<>RS232 controller) or TCP/IP via a remote RS232 (ser2net, ...)
## hanazeder requirements
Currently the script only reads registers
### register index
This is the number of the parameter or the port of the module (starting with 0)
## Getting started
1. install usbutils ```sudo apt-get install usbutils``` (if you're going to use the USB<>RS232 controller)
2. install python dependencies ```pipenv install```
3. add your script user to the ```tty```-group ```sudo addgroup pi tty```
## example usage
Read from a serial to TCP converter (like ser2net) at 192.168.1.2 port 2001 the register 1:
```python -m hanazeder.read --address 192.168.1.2 --port 2001 --register 1```
