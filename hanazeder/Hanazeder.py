from ast import Call
import asyncio
import serial
import time
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

class RequestTimeoutError(Exception):
    pass

class ShutdownError(Exception):
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
class ConfigEntry:
    key = 0

    def __init__(self, key, data: bytes):
        self.key = key
        self.value = data[0]
        self.max_value = data[1]
        self.min_value = data[2]
        self.change_step = data[3]

class HanazederRequestState(IntEnum):
    UNSENT = 0
    SENT = 1
    SUCCESSFUL = 2
    TIMEOUT = 3
    SHUTDOWN = 4
    DISCONNECTED = 5
class HanazederRequest:
    result = None
    def __init__(self, msg_no: int, type: int, decoder: DecoderCB):
        self.msg_no = msg_no
        self.type = type
        self.decoder = decoder
        self.created = time.monotonic()
        self.event = asyncio.Event()
        self.state = HanazederRequestState.UNSENT

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
        self.device.connected = False
        # Awake all listeners
        for request in self.device.queue:
            request.state = HanazederRequestState.DISCONNECTED
            request.event.set()

class HanazederFP:
    HEADER = b'\xEE'
    last_msg_num = 0
    connected = True
    debug = False
    connection: SerialOrNetwork
    queue: List[HanazederRequest] = []
    running = True

    def __init__(self, debug=False, request_timeout=2):
        self.debug = debug
        self.loop = asyncio.get_running_loop()
        self.queue_lock = asyncio.Lock()
        self.msg_no_lock = asyncio.Lock()
        self.request_timeout = request_timeout
    
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
        else:
            raise ConnectionInvalidError("Specify either address and port or serial port")
        self.reader = HanazederReader(self.connection, self.HEADER, self.debug)
        if serial_port:
            self.loop.add_reader(self.connection, self.read_byte)
        # Check queue for stuck messages periodically
        self.loop.create_task(self.check_queue())
    
    
    async def get_next_msg_no(self) -> int:
        async with self.msg_no_lock:
            msg_no = self.last_msg_num
            self.last_msg_num = (self.last_msg_num + 1) % 256
            # Avoid escape byte
            if self.last_msg_num == 238:
                self.last_msg_num = 239
            return msg_no
    
    async def send_msg(self, msg: bytes, decoder: DecoderCB) -> HanazederRequest:
        if self.debug:
            print(f'Sending msg {byte_to_hex(msg)}')
        request = HanazederRequest(msg[1], msg[2], decoder)
        async with self.queue_lock:
            self.queue.append(request)
        self.connection.write(msg)
        request.state = HanazederRequestState.SENT
        return request
    
    async def read_bytes(self, bytes):
        for byte in bytes:
            packet = self.reader.read(byte)
            if packet:
                await self.handle_packet(packet)
    
    def read_byte(self):
        self.loop.create_task(self.read_byte_async())
    
    async def read_byte_async(self):
        byte = self.connection.read(1)
        packet = self.reader.read(byte[0])
        if packet:
            await self.handle_packet(packet)
    
    async def check_queue(self):
        while self.connected:
            now = time.monotonic()
            async with self.queue_lock:
                for index, request in enumerate(self.queue):
                    if now - request.created > self.request_timeout:
                        print(f'Request #{request.msg_no} has timed out')
                        # TODO: resend
                        request.state = HanazederRequestState.TIMEOUT
                        request.event.set()
                        self.queue.pop(index)
            await asyncio.sleep(self.request_timeout)

    def shutdown(self):
        self.running = False       
        for request in self.queue:
            request.state = HanazederRequestState.SHUTDOWN
            request.event.set()


    async def handle_packet(self, packet: HanazederPacket):
        if self.debug:
            packet_debug = ""
            for req in self.queue:
                packet_debug = f"{packet_debug} #{req.msg_no}"
            print(f'Packet read #{packet.msg_no} type {packet.msg_type}: {packet.msg}.')
            print(f'Queue: {packet_debug}')
        found = False
        async with self.queue_lock:
            for index, req in enumerate(self.queue):
                if req.msg_no == packet.msg_no:
                    req.result = req.decoder(packet)
                    found = True
                    req.state = HanazederRequestState.SUCCESSFUL
                    req.event.set()
                    self.queue.pop(index)
                    break
            if not found:
                print(f"Couldn't find message {packet.msg_no} in queue!")

    async def handle_req_response(self, req: HanazederRequest):
        if req.state == HanazederRequestState.TIMEOUT:
            raise RequestTimeoutError()
        elif req.state == HanazederRequestState.SHUTDOWN:
            raise ShutdownError()
        elif req.state == HanazederRequestState.DISCONNECTED:
            raise NotConnectedError()
    
    async def create_read_information_msg(self) -> bool:
        return hanazeder_encode_msg(self.HEADER, await self.get_next_msg_no(), b'\x01\x00')
    
    async def read_information(self):
        req = await self.send_msg(await self.create_read_information_msg(), self.parse_information_packet)
        await req.event.wait()
        await self.handle_req_response(req)
    
    def parse_information_packet(self, msg: HanazederPacket):
        response = msg.msg
        # 00 f0 05 00 00 02 01 06 f9
        self.device_type = DeviceType(response[0])
        self.hardware_platform = HardwarePlatform(response[1])
        self.connection_flags = response[2]
        if (len(response) >= 5):
            self.version = f'{response[3]}.{response[4]}'
    
    async def create_read_sensor_msg(self, idx: int) -> bytes:
        request_bytes = bytes(b'\x04\x01') + idx.to_bytes(1, byteorder='little')
        return hanazeder_encode_msg(self.HEADER, await self.get_next_msg_no(), request_bytes)
    
    async def read_sensor(self, idx: int) -> float:
        if not self.connected:
            raise NotConnectedError()
        
        req = await self.send_msg(await self.create_read_sensor_msg(idx), self.parse_sensor_packet)
        await req.event.wait()
        await self.handle_req_response(req)
        return req.result
    
    def parse_sensor_packet(self, msg: HanazederPacket) -> float:
        value = hanazeder_decode_num(self.HEADER, msg.msg)
        return value
    
    async def create_read_config_block_msg(self, start: int, count: int) -> bytes:
        request = bytes(b'\x07\x03') + start.to_bytes(2, byteorder='little') + count.to_bytes(1, byteorder='little')
        return hanazeder_encode_msg(self.HEADER, await self.get_next_msg_no(), request)
    
    async def read_config_block(self, start: int, count: int) -> List[ConfigEntry]:
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
        req = await self.send_msg(await self.create_read_config_block_msg(start, count), parse_config_block_packet)
        await req.event.wait()
        await self.handle_req_response(req)
        return req.result

    async def create_read_sensor_name_msg(self, idx: int) -> bytes:
        request = bytes(b'\x13\x01') + idx.to_bytes(1, byteorder='little')
        return hanazeder_encode_msg(self.HEADER, await self.get_next_msg_no(), request)
    
    async def read_sensor_name(self, idx: int) -> str:
        if not self.connected:
            raise NotConnectedError()

        req = await self.send_msg(await self.create_read_sensor_name_msg(idx), self.parse_sensor_name_packet)
        await req.event.wait()
        await self.handle_req_response(req)
        return req.result
    
    def parse_sensor_name_packet (self, msg: HanazederPacket) -> str:
        if msg.msg and len(msg.msg) > 1:
            return msg.msg[1:].decode('ascii', errors='ignore').strip()
    
    async def create_read_debug_block_msg(self, start: int, count: int) -> bytes:
        request = bytes(b'\x20\x03') + dec_to_bytes(start) + count.to_bytes(1, byteorder='little')
        return hanazeder_encode_msg(self.HEADER, await self.get_next_msg_no(), request)
    
    async def read_debug_block(self, start: int, count: int, decoder: DecoderCB) -> Any:
        if not self.connected:
            raise NotConnectedError()
        req = await self.send_msg(await self.create_read_debug_block_msg(start, count), decoder)
        await req.event.wait()
        await self.handle_req_response(req)
        return req.result
    
    async def read_energy(self) -> EnergyReading:
        return await self.read_debug_block(313, 8, self.parse_energy_packet)
    
    def parse_energy_packet(self, msg: HanazederPacket) -> Tuple[int, int, int]:
        total = hanazeder_decode_num(self.HEADER, msg.msg[0:2])
        current = hanazeder_decode_num(self.HEADER, msg.msg[2:4])
        impulse = hanazeder_decode_num(self.HEADER, msg.msg[4:6])
        return (total, current, impulse)
    

