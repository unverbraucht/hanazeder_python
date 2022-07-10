from .Hanazeder import HanazederFP
import argparse
import sys

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial-port", help="set serial port",
                    type=str)
    parser.add_argument("--register", help="register to read",
                    type=int)
    args = parser.parse_args()

    conn = HanazederFP(serial_port=args.serial_port)
    conn.connect()
    value = conn.read_register(parser.register)
    print(f'Register {args.register} is {value}')
    return 0

if __name__ == '__main__':
    sys.exit(main())