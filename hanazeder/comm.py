from .types import SerialOrNetwork
from .encoding import *

from serial import Serial
from crccheck.crc import Crc8Maxim

SENSOR_GONE = b'\xFF\x7F'

class ReadtimeoutException(Exception):
    pass

class ChecksumNotMatchingException(Exception):
    pass

class InvalidHeaderException(Exception):
    pass

class IllegalArgumentException(Exception):
    pass

def hanazeder_decode_num(header, value) -> float:
    unescaped = value.replace(header + header, header)
    if unescaped == SENSOR_GONE:
        return None
    int_val = int.from_bytes(value, byteorder='little', signed=True)
    return int_val / 10

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
    checksum = connection.read()
    crc = Crc8Maxim()
    crc.process(header[1:])
    crc.process(value)
    calculated_crc = crc.finalbytes()
    if calculated_crc != checksum:
        raise ChecksumNotMatchingException(f'Expected checksum {calculated_crc} but got {checksum}')
    return value

def hanazeder_encode_msg(header: bytes, msg_num: int, request: bytes) -> bytes:
    if msg_num < 0 or msg_num > 255:
        raise IllegalArgumentException("msg_num must be between 0 and 255")
    if len(header) != 1:
        raise IllegalArgumentException("header must be single byte")
    msg = bytearray(header)
    msg.append(msg_num)
    msg += bytearray(request)
    checksum = Crc8Maxim.calcbytes(msg[1:])
    msg += bytearray(checksum)
    return bytes(msg)