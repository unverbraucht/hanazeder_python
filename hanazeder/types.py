import serial
import socket
from typing import Union, Tuple

SerialOrNetwork = Union[socket.socket, serial.Serial, bytearray]

EnergyReading = Tuple[float, float, float]