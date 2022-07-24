from ..hanazeder.encoding import *

def test_hex_to_byte():
    assert hex_to_byte("01 02 03") == b'\x01\x02\x03'
    assert hex_to_byte("EE 0A 23") == b'\xEE\x0A\x23'

def test_byte_to_hex():
    assert byte_to_hex(b'\01\02\03') == "010203"