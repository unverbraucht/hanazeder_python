from ..hanazeder.comm import *

import io
import pytest

HEADER=b'\xEE'

def test_read_sensor():
    assert hanazeder_decode_num(HEADER, b'\x55\x01') == 34.1

def test_read_nonexistant():
    assert hanazeder_decode_num(HEADER, b'\xFF\x7F') == None

def test_hanazeder_read():
    fake_stream = io.BytesIO(hex_to_byte("EE03F0025501A6"))
    read_value = hanazeder_read(HEADER, 3, fake_stream)
    assert read_value == b'\x55\x01'

def test_hanazeder_read_checksum():
    fake_stream = io.BytesIO(hex_to_byte("EE03F0025501A7"))
    with pytest.raises(ChecksumNotMatchingException):
        hanazeder_read(HEADER, 3, fake_stream)

def test_hanazeder_read_header():
    fake_stream = io.BytesIO(hex_to_byte("EA03F0025501A7"))
    with pytest.raises(InvalidHeaderException):
        hanazeder_read(HEADER, 3, fake_stream)
    fake_stream = io.BytesIO(hex_to_byte("EE03F0025501A7"))
    with pytest.raises(InvalidHeaderException):
        hanazeder_read(HEADER, 4, fake_stream)

def test_hanazeder_write():
    msg = hanazeder_encode_msg(HEADER, 1, b'\x04\x01\x00')
    assert msg == hex_to_byte('EE01040100D5')
    msg = hanazeder_encode_msg(HEADER, 16, hex_to_byte('20033F0103'))
    assert msg == hex_to_byte('EE1020033F01038C')
    # Also test initial handshake
    msg = hanazeder_encode_msg(HEADER, 0, b'\x01\x00')
    assert msg == hex_to_byte('EE 00 01 00 C4')