#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
   Copyright 2016 Thomas Binder

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.


 Script:  hanazeder_read.py
 Author:  Thomas Binder
 Date:    November 23, 2016
 Purpose: connects to the hanazeder HLC20 and reads the outputs

"""

import re, os, time
import serial

## Konfiguration ##

# serial port for hanazeder
RS232_DEVICE 	= "/dev/ttyUSB0"		# Path to your RS232-device, e.g. /dev/ttyUSB0 for USB port or /dev/ttyS0 for serial port

# Variablen
jetzt = str(int(time.mktime(time.localtime())))

# Funktionen
def HexToByte(hexStr):
    """
    Convert a string hex byte values into a byte string. The Hex Byte values may
    or may not be space separated.
    """
    hexStr = ''.join( hexStr.split(" ") )
    return ''.join( ["%c" % chr( int ( hexStr[i:i+2],16 ) ) for i in range(0, len( hexStr ), 2) ] )
	
def ByteToHex(byteStr):
    """
    Convert a byte string to it's hex string representation e.g. for output.
    """
    return''.join( [ "%02X " % ord( x ) for x in byteStr]).strip()

def DecToHex(decStr):
    """return the hexadecimal string representation of integer n"""
    hexStr = hex((1 << 16) + decStr)[2:]
    if len(hexStr) > 4:
        hexStr = hexStr[1:]
    return hexStr[:2] + " " + hexStr[2:]

def HLC20read(modnr, partyp, parind):
    """Reads from HLC20 and returns the response"""
    byte = HexToByte('98 ' + modnr + ' ' + partyp + ' ' + parind)
    print("\n>"+ByteToHex(byte))
    ser.write(byte)
    time.sleep(0.1)
    x=ser.read(1024)
    print(ByteToHex(x))
    erg = ByteToHex(x).split(' ', 3)
    return int(str(erg[1])+str(erg[2]), 16)

def HLC20write(modnr, partyp, parind, wert):
    """
    Writes to HLC20 and returns the response
    98 01 1F 01 00
    99 01 1F 01 00 01 c2
    """
    byte = HexToByte('99 ' + modnr + ' ' + partyp + ' ' + parind + ' ' + DecToHex(int(wert)))
    print("\n>"+ByteToHex(byte))
    ser.write(byte)
    time.sleep(0.2)
    x=ser.read(1024)
    print(ByteToHex(x))
    erg = ByteToHex(x).split(' ', 3)
    return int(str(erg[1])+str(erg[2]), 16)

# Serielle Verbindung oeffnen
ser = serial.Serial(
    port=RS232_DEVICE,
    baudrate = 38400,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=0.1
)

# Initialisierung Vebindung zur HLC20 (95 30 73)
byte = HexToByte('EE 00 01 00 C4')
print("\n>"+ByteToHex(byte))
ser.write(byte)
time.sleep(1)
x=ser.read(1024)
print(ByteToHex(x))

# # Sensorenabfrage
# cur.execute("SELECT * FROM `hanazeder_config` WHERE status = 1;")
# rows = cur.fetchall()
# for row in rows:
#     wert = HLC20read(row[6], row[7], row[8])
#     print row[4]
#     if wert > 32767:
#         wert -= 65536
#     if row[4] == "temp":
#         wert = float(wert)/10
#     print wert
#     sqlquery = "INSERT INTO `hanazeder_werte` (`time`, `sensor`, `value`) VALUES (FROM_UNIXTIME("+jetzt+"), "+str(row[0])+", "+str(wert)+");"
#     cur.execute(sqlquery)
#     con.commit()
#     print 'curl --header "Content-Type: text/plain" --request PUT --data "' + str(wert) + '" http://' + OPENHAB_SERVER + ':' + OPENHAB_PORT + '/rest/items/' + str(row[10]) + '/state'
#     os.system('curl --header "Content-Type: text/plain" --request PUT --data "' + str(wert) + '" http://' + OPENHAB_SERVER + ':' + OPENHAB_PORT + '/rest/items/' + str(row[10]) + '/state')

# ser.close()