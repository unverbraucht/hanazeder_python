import serial
import socket
from enum import IntEnum
from typing import List

from .types import SerialOrNetwork, EnergyReading
from .comm import hanazeder_decode_byte, hanazeder_encode_msg, hanazeder_read, hanazeder_decode_num
from .encoding import dec_to_bytes, byte_to_hex

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

SENSOR_LABELS = [
    None,
    "Kollektor",
    "Sonnenf.",
    "Koll-RL",
    "Boiler",
    "Boiler 1",
    "Boiler 2",
    "Boiler/U",
    "Boil.1/U",
    "Boil.2/U",
    "Boiler/M",
    "Boil.1/M",
    "Boil.2/M",
    "Boiler/O",
    "Boil.1/O",
    "Boil.2/O",
    "Puffer",
    "Puffer 1",
    "Puffer 2",
    "Puffer/U",
    "Puff.1/U",
    "Puff.2/U",
    "Puffer/M",
    "Puff.1/M",
    "Puff.2/M",
    "Puffer/O",
    "Puff.1/O",
    "Puff.2/O",
    "Speicher",
    "Speich.1",
    "Speich.2",
    "Speich/U",
    "Spei.1/U",
    "Spei.2/U",
    "Speich/M",
    "Spei.1/M",
    "Spei.2/M",
    "Speich/O",
    "Spei.1/O",
    "Spei.2/O",
    "Unten",
    "Mitte",
    "Oben",
    "Vorlauf",
    "Ruecklauf",
    "Warmwass.",
    "Kaltwass.",
    "Tauscher",
    "Plattent.",
    "Heizkreis",
    "Heizkrs.1",
    "Heizkrs.2",
    "Heizkrs.3",
    "Heizkoerp",
    "Bodenheiz",
    "Heiz-Kes.",
    "Kessel 1",
    "Kessel 2",
    "Holz-Kes.",
    "Oel-Kess.",
    "Gas-Kess.",
    "Waermepu.",
    "Pelletsk.",
    "Hackgutk.",
    "Brenner",
    "Ofen",
    "Schwimmb.",
    "Becken",
    "Bad",
    "Raumtemp.",
    "Raumtmp.1",
    "Raumtmp.2",
    "Aussentmp",
    "Keller",
    "Erdgesch.",
    "1.Stock",
    "2.Stock",
    "3.Stock",
    "Koll-Sued",
    "Koll-West",
    "Koll-Ost",
    "Raum-Regl.",
    "VL Solar",
    "RL Solar",
    "RL Kessel",
    "VL Heizk.",
    "VL Bodenh",
    "VL Wandh.",
    "Wintergar",
    "Treibhaus",
    "Nicht bel"
]

class ConfigEntry:
    key = 0

    def __init__(self, key, data: bytes):
        self.key = key
        self.value = data[0]
        self.max_value = data[1]
        self.min_value = data[2]
        self.change_step = data[3]

class HanazederFP:
    HEADER = b'\xEE'
    last_msg_num = 0
    connected = True
    debug = False
    connection: SerialOrNetwork

    def __init__(self,
        serial_port="/dev/ttyUSB0",
        address=None,
        port=None,
        debug=False,
        timeout=1000):
        self.debug = debug
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
        if self.debug:
            print(f'Sending msg {byte_to_hex(msg)}')
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
    
    def create_read_sensor_msg(self, idx: int) -> bytes:
        request = bytes(b'\x04\x01') + idx.to_bytes(1, byteorder='little')
        return hanazeder_encode_msg(self.HEADER, self.last_msg_num, request)
    
    def read_sensor(self, idx: int) -> float:
        if not self.connected:
            raise NotConnectedError()
        msg_num = self.send_msg(self.create_read_sensor_msg(idx))
        response = hanazeder_read(self.HEADER, msg_num, self.connection)
        value = hanazeder_decode_num(self.HEADER, response)
        return value
    
    def create_read_config_block_msg(self, start: int, count: int) -> bytes:
        request = bytes(b'\x07\x03') + start.to_bytes(2, byteorder='little') + count.to_bytes(1, byteorder='little')
        return hanazeder_encode_msg(self.HEADER, self.last_msg_num, request)
    
    def read_config_block(self, start: int, count: int) -> List[ConfigEntry]:
        if not self.connected:
            raise NotConnectedError()
        msg_num = self.send_msg(self.create_read_config_block_msg(start, count))
        response = hanazeder_read(self.HEADER, msg_num, self.connection)
        entries = []
        for x in range(0, int(round(len(response) / 4))):
            chunk = response[x * 4: (x + 1) * 4]
            entry = ConfigEntry(start + x, chunk)
            entries.append(entry)
        return entries

    
    def create_read_sensor_name_msg(self, idx: int) -> bytes:
        request = bytes(b'\x13\x01') + idx.to_bytes(1, byteorder='little')
        return hanazeder_encode_msg(self.HEADER, self.last_msg_num, request)
    
    def read_sensor_name(self, idx: int) -> str:
        if not self.connected:
            raise NotConnectedError()
        msg_num = self.send_msg(self.create_read_sensor_name_msg(idx))
        response = hanazeder_read(self.HEADER, msg_num, self.connection)
        if response and len(response) > 1:
            return response[1:].decode('ascii', errors='ignore').strip()
    
    def create_read_debug_block_msg(self, start: int, count: int) -> bytes:
        request = bytes(b'\x20\x03') + dec_to_bytes(start) + count.to_bytes(1, byteorder='little')
        return hanazeder_encode_msg(self.HEADER, self.last_msg_num, request)
    
    def read_debug_block(self, start: int, count: int) -> bytes:
        if not self.connected:
            raise NotConnectedError()
        msg_num = self.send_msg(self.create_read_debug_block_msg(start, count))
        response = hanazeder_read(self.HEADER, msg_num, self.connection)
        return response
    
    def read_energy(self) -> EnergyReading:
        response = self.read_debug_block(313, 8)
        total = hanazeder_decode_num(self.HEADER,response[0:2])
        current = hanazeder_decode_num(self.HEADER,response[2:4])
        impulse = hanazeder_decode_num(self.HEADER,response[4:6])
        return (total, current, impulse)

