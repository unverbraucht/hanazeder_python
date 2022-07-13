import serial
import socket
from enum import IntEnum


from .types import SerialOrNetwork
from .comm import hanazeder_decode_byte, hanazeder_encode_msg, hanazeder_read, hanazeder_decode_num


class ConnectError(Exception):
    pass

class NotConnectedError(Exception):
    pass

class ConnectionInvalidError(Exception):
    pass

class DeviceType(IntEnum):
    FP10 = 0
    FP6 = 1
    FP3 = 2
    FP2 = 3
    FP1 = 4
    SH3 = 5
    SH2 = 6
    SH1 = 7

class HardwarePlatform(IntEnum):
    FP10 = 0
    FP3 = 1

class HanazederFP:
    HEADER = b'\xEE'
    last_msg_num = 0
    connected = True
    connection: SerialOrNetwork

    def __init__(self,
        serial_port="/dev/ttyUSB0",
        address=None,
        port=None,
        timeout=1000):
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
            self.connection = socket.create_connection((address, port), timeout).makefile('rwb')
        else:
            raise ConnectionInvalidError("Specify either address and port or serial port")
    
    def send_msg(self, msg: bytes) -> bool:
        self.connection.write(msg)
        self.connection.flush()
        msg_num = self.last_msg_num
        self.last_msg_num = (self.last_msg_num + 1) % 256
        return msg_num

    
    def create_read_information_msg(self) -> bool:
        return hanazeder_encode_msg(self.HEADER, self.last_msg_num, b'\x01\x00')
    
    def read_information(self) -> bool:
        msg_num = self.send_msg(self.create_read_information_msg())
        response = hanazeder_read(self.HEADER, msg_num, self.connection)
        # 00 f0 05 00 00 02 01 06 f9
        self.device_type = DeviceType(response[0])
        self.hardware_platform = HardwarePlatform(response[1])
        self.connection_flags = response[2]
        if (len(response) >= 5):
            self.version = f'{response[3]}.{response[4]}'

        self.connected = True
        return self.connected
    
    def create_read_sensor_msg(self, register: int) -> bytes:
        request = bytes(b'\x04\x01') + register.to_bytes(1, byteorder='big')
        return hanazeder_encode_msg(self.HEADER, self.last_msg_num, request)
    
    def read_sensor(self, register: int) -> float:
        if not self.connected:
            raise NotConnectedError()
        msg_num = self.send_msg(self.create_read_sensor_msg(register))
        response = hanazeder_read(self.HEADER, msg_num, self.connection)
        value = hanazeder_decode_num(self.HEADER, response)
        return value
        
