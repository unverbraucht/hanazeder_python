import serial
import socket
from typing import Union

SerialOrNetwork = Union[socket.socket, serial.Serial, bytearray]