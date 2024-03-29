from enum import IntEnum
from .types import SerialOrNetwork
from .encoding import *

import logging
from crccheck.crc import Crc8Maxim

logger = logging.getLogger('hanazeder.comm')

SENSOR_GONE = b'\xFF\x7F'

class ReadtimeoutException(Exception):
    pass

class ChecksumNotMatchingException(Exception):
    pass

class InvalidHeaderException(Exception):
    pass

class IllegalArgumentException(Exception):
    pass

class ReaderState(IntEnum):
    LOOKING_FOR_HEADER = 0
    EXPECTING_MSG_NO = 1
    EXPECTING_TYPE = 2
    EXPECTING_AFTER_TYPE = 3
    EXPECTING_SIZE = 4
    READING_PAYLOAD = 5
    EXPECTING_CHECKSUM = 6
    ESCAPING = 7


class HanazederPacket:
    msg_no = None
    msg_type = None
    msg_size = None
    msg = None
class HanazederReader:
    state = ReaderState.LOOKING_FOR_HEADER
    state_before_escaping = None
    packet: HanazederPacket = None

    def __init__(self, connection, header, debug):
        self.connection = connection
        self.header = header[0]
        self.debug = debug
    
    def read(self, byte: int) -> HanazederPacket:
        finished_packet = self.handle_byte(byte)
        if finished_packet:
            return finished_packet

    def handle_byte(self, byte: int) -> HanazederPacket:
        if self.state != ReaderState.LOOKING_FOR_HEADER \
                and self.state != ReaderState.EXPECTING_CHECKSUM \
                and self.state != ReaderState.ESCAPING:
            self.crc.process(byte.to_bytes(1, byteorder='little'))
        if self.debug:
            logger.debug('Handle_byte %X state in %s', byte, self.state.name)
        
        if byte == self.header and self.state != ReaderState.LOOKING_FOR_HEADER \
                and self.state != ReaderState.ESCAPING:
            if self.debug:
                logger.debug('Found escape byte, skipping')
            self.state_before_escaping = self.state
            self.state = ReaderState.ESCAPING
            return
        
        if self.state == ReaderState.ESCAPING:
            self.state = self.state_before_escaping
            self.state_before_escaping = None

        if self.state == ReaderState.LOOKING_FOR_HEADER:
            if byte == self.header:
                self.packet = HanazederPacket()
                self.state = ReaderState.EXPECTING_MSG_NO
                self.crc = Crc8Maxim()
        elif self.state == ReaderState.EXPECTING_MSG_NO:
            self.packet.msg_no = byte
            self.state = ReaderState.EXPECTING_TYPE
        elif self.state == ReaderState.EXPECTING_TYPE:
            self.packet.msg_type = byte
            self.state = ReaderState.EXPECTING_SIZE
        elif self.state == ReaderState.EXPECTING_SIZE:
            self.packet.msg_size = byte
            self.packet.msg = bytearray()
            if self.packet.msg_size == 0:
                self.state = ReaderState.EXPECTING_CHECKSUM
            else:
                self.state = ReaderState.READING_PAYLOAD
        elif self.state == ReaderState.READING_PAYLOAD or self.state == ReaderState.ESCAPING:
            self.packet.msg += bytearray(byte.to_bytes(1, byteorder='little'))
            self.packet.msg_size = self.packet.msg_size - 1
            if self.packet.msg_size <= 0:
                self.state = ReaderState.EXPECTING_CHECKSUM
            else:
                self.state = ReaderState.READING_PAYLOAD
        elif self.state == ReaderState.EXPECTING_CHECKSUM:
            self.state = ReaderState.LOOKING_FOR_HEADER
            calculated_crc = self.crc.finalbytes()
            if calculated_crc[0] != byte:
                logger.error('Wrong checksum')
            else:
                # Packet fully read
                return self.packet
        if self.debug:
            logger.debug('Handle_byte state out %s', self.state.name)


def hanazeder_decode_num(value, signed=True) -> float:
    if value == SENSOR_GONE:
        return None
    int_val = int.from_bytes(value, byteorder='little', signed=signed)
    return int_val / 10

def hanazeder_decode_byte(byte: bytes) -> int:
    return int.from_bytes(byte, byteorder='little')

def hanazeder_read(expected_header: bytes, msg_num: int, connection: SerialOrNetwork) -> bytes:
    # start by reading at least four bytes
    header = connection.read(4)
    if len(header) < 4:
        raise ReadtimeoutException("Could not read header")
    if header[0] is not expected_header[0]:
        raise InvalidHeaderException(f'Expecting header {expected_header[0]}, got {header[0]} instead')
    if header[1] != msg_num:
        raise InvalidHeaderException(f'Expecting message number {msg_num} but got {header[1]}')
    value_size = header[3]
    value = connection.read(value_size)
    # Always followed by one byte checksum
    checksum = connection.read(1)
    crc = Crc8Maxim()
    crc.process(header[1:])
    crc.process(value)
    calculated_crc = crc.finalbytes()
    if calculated_crc != checksum:
        raise ChecksumNotMatchingException(f'Expected checksum {calculated_crc} but got {checksum}')
    # TODO: unescape header in value
    return value

def hanazeder_encode_msg(header: bytes, msg_num: int, request: bytes) -> bytes:
    if msg_num < 0 or msg_num > 255:
        raise IllegalArgumentException("msg_num must be between 0 and 255")
    if len(header) != 1:
        raise IllegalArgumentException("header must be single byte")
    # Checksum is without header
    checksum_msg = bytearray()
    checksum_msg.append(msg_num)
    checksum_msg += bytearray(request)
    checksum = Crc8Maxim.calcbytes(checksum_msg)
    # Escape header in request
    escaped_msg = bytearray(header) + bytearray(checksum_msg.replace(b'\xEE', b'\xEE\xEE')) + bytearray(checksum)
    # msg += bytearray(checksum)
    
    return bytes(escaped_msg)