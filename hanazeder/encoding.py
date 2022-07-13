def hex_to_byte(hexStr: str) -> bytes:
    """
    Convert a string hex byte values into a byte string. The Hex Byte values may
    or may not be space separated.
    """
    hexStr = ''.join(hexStr.split(" "))
    return bytes.fromhex(hexStr)
	
def byte_to_hex(bytes: bytes) -> str:
    """
    Convert a byte string to it's hex string representation e.g. for output.
    """
    return bytes.hex()

def dec_to_bytes(decimal: int):
    """return the hexadecimal string representation of integer n"""
    return decimal.to_bytes(2, byteorder='little')