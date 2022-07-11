import serial
import socket
from typing import TypeAlias

SerialOrNetwork: TypeAlias = socket.socket | serial.Serial | bytearray