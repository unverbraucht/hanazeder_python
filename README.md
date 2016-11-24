# serial_hlc20
serial connection to hanazeder HLC20 home automation controller
# DISCLAIMER
With this connection, you could change all the values of your HLC20 controller, which could result to a non-functional heating! Be careful, what parameter you're about to write. If you're only using read, you're safe!
I don't take responsibilities for any damage or mis-interpretation caused by the python script. Use it at your own risk!
## Hardware requirements
This python script opens a serial connection to the hanazeder HLC20 home automation controller (http://www.hanazeder.at/en_US/page/hlc) and reads out the values of the programmed modules (e.g. temperature sensors, valve statusses, ...).
1. hanazeder HLC20
2. serial connection (either direct or via USB<>RS232 controller
## hanazeder requirements
You need to know the module numbers and the module types of the HLC20 programming. Within HLC20 you (or you installer) did some programming for the respective modules. If you're not sure, what this means, you must ask your heating installer, if he can export you a list of the modules from the programming software.
There are different types and they have to be known, if you query the HLC20:
### module number
This is the ID of the module in HLC20.
### parameter types
This is the parameter of the module, you want to read
1. "01" = short parameter (analoge value)
2. "03" = select parameter (drop down)
3. "F0" = module input
4. "f1" = module output
### parameter index
This is the number of the parameter or the port of the module (starting with 0)
## Getting started
1. install usbutils ```sudo apt-get install usbutils``` (if you're going to use the USB<>RS232 controller)
2. install the MySQLdb module for python ```sudo apt-get install python-mysqldb```
3. install the serial module for python ```sudo apt-get install python-serial```
4. add your script user to the ```tty```-group ```sudo addgroup pi tty```
## example usage
Let's say, you want to read the values of the outside temperature sensor and you looked up the configuration of the hanazeder HLC20:
* module number: ```00 01```
* parameter type: ```F1```
* parameter index: ```00```
1. handshake with your HLC20
2. putting the code "```98 00 01 F1 00```" in byte to your HLC20
3. reading the response (also byte)
4. converting the response to hex
5. interpreting the response
6. putting the response to openHAB via the openHAB API
