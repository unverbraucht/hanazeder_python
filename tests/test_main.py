from ..hanazeder.Hanazeder import HanazederFP
from ..hanazeder.encoding import hex_to_byte

from unittest.mock import MagicMock

def test_create_instance(mocker):
    mocker.patch('serial.Serial')
    inst = HanazederFP()
    assert inst.connected == False

def test_read_register_msg(mocker):
    mocker.patch('serial.Serial')
    inst = HanazederFP()
    msg = inst.create_read_register_msg(1)
    assert msg == hex_to_byte('EE01040100D5')

# def test_connection(mocker):
#     def mocked_read():
#         return b'\xee\x00\xf0\x05\x00\x00\x02\x01\x06\xf9'

# def test_read_register(mocker):
#     mocked_read_content = hex_to_byte('EE01F0023800A8')

#     mocker.patch('serial.Serial')
#     mocker.patch('serial.Serial.write')
#     mocker.patch('serial.Serial.read', return_value=mocked_read_content)
#     inst = HanazederFP()
#     inst.connected = True
#     msg = inst.read_register(1)
#     assert msg == mocked_read_content