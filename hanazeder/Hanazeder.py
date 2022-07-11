import serial
import socket

from .types import SerialOrNetwork
from .comm import hanazeder_encode_msg, hanazeder_read, hanazeder_decode_num


class ConnectError(Exception):
    pass

class NotConnectedError(Exception):
    pass

class ConnectionInvalidError(Exception):
    pass

class HanazederFP:
    HEADER = b'\xEE'
    last_msg_num = 1
    connected = False
    connection: SerialOrNetwork

    def __init__(self,
        serial_port="/dev/ttyUSB0",
        address=None,
        port=None,
        timeout=1):
        if serial_port:
            self.connection = serial.Serial(
                port=serial_port,
                baudrate = 38400,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=timeout
            )
        elif address and port:
            self.connection = socket.create_connection((address, port), timeout).makefile()
        else:
            raise ConnectionInvalidError("Specify either address and port or serial port")
    
    def connect(self) -> bool:
        handshake = hanazeder_encode_msg(self.HEADER, 0, b'\x01\x00')
        self.connection.write(handshake)
        response = self.connection.read(size=10)
        if response is not b'\xee\x00\xf0\x05\x00\x00\x02\x01\x06\xf9':
            raise ConnectError(f'Wrong response for handshake, got {response}')
        self.connected = True
        return self.connected
    
    def create_read_register_msg(self, register: int) -> bytes:
        request = bytes(b'\x04\x01') + bytes(register)
        return hanazeder_encode_msg(self.HEADER, self.last_msg_num, request)
    
    def read_register(self, register: int) -> float:
        if not self.connected:
            raise NotConnectedError()
        self.last_msg_num = (self.last_msg_num + 1) % 256
        msg = self.create_read_register_msg(register)
        self.connection.write(msg)
        response = hanazeder_read(self.HEADER, self.last_msg_num, self.connection)
        value = hanazeder_decode_num(self.HEADER, response)
        return value
        
