from ast import Call
import asyncio
import serial
import socket
from enum import IntEnum
from typing import Any, Callable, List, Tuple

from .types import SerialOrNetwork, EnergyReading
from .comm import HanazederPacket, HanazederReader, hanazeder_encode_msg, hanazeder_read, hanazeder_decode_num
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

DecoderCB = Callable[[HanazederPacket], Any]

ParseCB = Callable[[Any], Any]
class ConfigEntry:
    key = 0

    def __init__(self, key, data: bytes):
        self.key = key
        self.value = data[0]
        self.max_value = data[1]
        self.min_value = data[2]
        self.change_step = data[3]

class HanazederRequest:
    def __init__(self, msg_no: int, type: int, cb: ParseCB, decoder: DecoderCB):
        self.msg_no = msg_no
        self.cb = cb
        self.type = type
        self.decoder = decoder

class FPProtocol(asyncio.Protocol):
    device = None
    def connection_made(self, transport):
        self.connection = transport

    def data_received(self, data):
        if self.device.debug:
            print(f'Data received: {data}')
        asyncio.get_event_loop().create_task(self.device.read_bytes(data))

    def connection_lost(self, exc):
        print('The server closed the connection')
        print('Stop the event loop')
        self.device.loop.stop()
class HanazederFP:
    HEADER = b'\xEE'
    last_msg_num = 0
    connected = True
    debug = False
    connection: SerialOrNetwork
    queue: List[HanazederRequest] = []

    def __init__(self, debug=False):
        self.debug = debug
        self.loop = asyncio.get_running_loop()
        self.queue_empty_event = asyncio.Event()
    
    async def open(self,
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
            (self.connection, proto) = await self.loop.create_connection(FPProtocol, address, port)
            proto.device = self
            # self.connection = socket.create_connection((address, port), timeout).makefile('rwb')
        else:
            raise ConnectionInvalidError("Specify either address and port or serial port")
        self.reader = HanazederReader(self.connection, self.HEADER, self.debug)
        if serial_port:
            self.loop.add_reader(self.connection, self.read_byte)
    
    async def wait_for_empty_queue(self):
        await self.queue_empty_event.wait()
    
    async def send_msg(self, msg: bytes, cb: ParseCB, decoder: DecoderCB) -> bool:
        if self.debug:
            print(f'Sending msg {byte_to_hex(msg)}')
        self.queue.append(HanazederRequest(msg[1], msg[2], cb, decoder))
        self.queue_empty_event.clear()
        self.connection.write(msg)
        # await self.connection.flush()
        msg_num = self.last_msg_num
        self.last_msg_num = (self.last_msg_num + 1) % 256
        return msg_num
    
    async def read_bytes(self, bytes):
        for byte in bytes:
            packet = self.reader.read(byte)
            if packet:
                await self.handle_packet(packet)
    
    async def read_byte(self):
        byte = self.connection.read(1)
        packet = self.reader.read(byte[0])
        if packet:
            await self.handle_packet(packet)

    async def handle_packet(self, packet: HanazederPacket):
        if self.debug:
            print(f'Packet read: {packet}')
        found = False
        for index, req in enumerate(self.queue):
            if req.msg_no == packet.msg_no:
                await req.cb(req.decoder(packet))
                found = True
                self.queue.pop(index)
                break
        if not found:
            print(f"Couldn't find message {packet.msg_no} in queue!")
        else:
            if len(self.queue) == 0:
                self.queue_empty_event.set()

    
    def create_read_information_msg(self) -> bool:
        return hanazeder_encode_msg(self.HEADER, self.last_msg_num, b'\x01\x00')
    
    async def read_information(self, cb: Callable[[None], Any]):
        await self.send_msg(self.create_read_information_msg(), cb, self.parse_information_packet)
    
    def parse_information_packet(self, msg: HanazederPacket):
        response = msg.msg
        # 00 f0 05 00 00 02 01 06 f9
        self.device_type = DeviceType(response[0])
        self.hardware_platform = HardwarePlatform(response[1])
        self.connection_flags = response[2]
        if (len(response) >= 5):
            self.version = f'{response[3]}.{response[4]}'
    
    def create_read_sensor_msg(self, idx: int) -> bytes:
        request = bytes(b'\x04\x01') + idx.to_bytes(1, byteorder='little')
        return hanazeder_encode_msg(self.HEADER, self.last_msg_num, request)
    
    async def read_sensor(self, idx: int, cb: Callable[[int, float], Any]):
        if not self.connected:
            raise NotConnectedError()
        
        async def cb_wrapper(value: float):
            await cb(idx, value)
        await self.send_msg(self.create_read_sensor_msg(idx), cb_wrapper, self.parse_sensor_packet)
    
    def parse_sensor_packet(self, msg: HanazederPacket) -> float:
        value = hanazeder_decode_num(self.HEADER, msg.msg)
        return value
    
    def create_read_config_block_msg(self, start: int, count: int) -> bytes:
        request = bytes(b'\x07\x03') + start.to_bytes(2, byteorder='little') + count.to_bytes(1, byteorder='little')
        return hanazeder_encode_msg(self.HEADER, self.last_msg_num, request)
    
    async def read_config_block(self, start: int, count: int, cb: Callable[[List[ConfigEntry]], Any]):
        if not self.connected:
            raise NotConnectedError()
        
        def parse_config_block_packet(msg: HanazederPacket) -> List[ConfigEntry]:
            response = msg.msg
            entries = []
            for x in range(0, int(round(len(response) / 4))):
                chunk = response[x * 4: (x + 1) * 4]
                entry = ConfigEntry(start + x, chunk)
                entries.append(entry)
            return entries
        await self.send_msg(self.create_read_config_block_msg(start, count), cb, parse_config_block_packet)

    def create_read_sensor_name_msg(self, idx: int) -> bytes:
        request = bytes(b'\x13\x01') + idx.to_bytes(1, byteorder='little')
        return hanazeder_encode_msg(self.HEADER, self.last_msg_num, request)
    
    async def read_sensor_name(self, idx: int, cb: Callable[[int, str], Any]):
        if not self.connected:
            raise NotConnectedError()

        async def cb_wrapper(name: str):
            await cb(idx, name)
        await self.send_msg(self.create_read_sensor_name_msg(idx), cb_wrapper, self.parse_sensor_name_packet)
    
    def parse_sensor_name_packet (self, msg: HanazederPacket) -> str:
        if msg.msg and len(msg.msg) > 1:
            return msg.msg[1:].decode('ascii', errors='ignore').strip()
    
    def create_read_debug_block_msg(self, start: int, count: int) -> bytes:
        request = bytes(b'\x20\x03') + dec_to_bytes(start) + count.to_bytes(1, byteorder='little')
        return hanazeder_encode_msg(self.HEADER, self.last_msg_num, request)
    
    async def read_debug_block(self, start: int, count: int, cb: Callable[[Any], Any], decoder: DecoderCB) -> bytes:
        if not self.connected:
            raise NotConnectedError()
        await self.send_msg(self.create_read_debug_block_msg(start, count), cb, decoder)
    
    async def read_energy(self, cb: Callable[[Tuple[int, int, int]], Any]) -> EnergyReading:
        await self.read_debug_block(313, 8, cb, self.parse_energy_packet)
    
    def parse_energy_packet(self, msg: HanazederPacket) -> Tuple[int, int, int]:
        total = hanazeder_decode_num(self.HEADER, msg.msg[0:2])
        current = hanazeder_decode_num(self.HEADER, msg.msg[2:4])
        impulse = hanazeder_decode_num(self.HEADER, msg.msg[4:6])
        return (total, current, impulse)
    

