import serial

from .comm import hanazeder_encode_msg, hanazeder_read, hanazeder_decode_num

class ConnectError(Exception):
    pass

class NotConnectedError(Exception):
    pass

class HanazederFP:
    HEADER = b'\xEE'
    last_msg_num = 1
    connected = False

    def __init__(self,
        serial_port="/dev/ttyUSB0",
        timeout=1):
        self.serial = serial.Serial(
            port=serial_port,
            baudrate = 38400,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=timeout
        )
    
    def connect(self) -> bool:
        handshake = hanazeder_encode_msg(self.HEADER, 0, b'\x01\x00')
        self.serial.write(handshake)
        response = self.serial.read(size=10)
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
        self.serial.write(msg)
        response = hanazeder_read(self.HEADER, self.last_msg_num, self.serial)
        value = hanazeder_decode_num(self.HEADER, response)
        return value
        
