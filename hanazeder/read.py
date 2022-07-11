from .Hanazeder import HanazederFP
import argparse
import sys

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial-port", help="set serial port",
                    type=str)
    parser.add_argument("--register", help="register to read",
                    type=int)
    parser.add_argument("--address", help="connect to HOSTNAME, needs port as well",
                    type=str)
    parser.add_argument("--port", help="connect to HOSTNAME on port PORT",
                    type=int, default=5000)
    args = parser.parse_args()

    if args.address and args.serial_port:
        print('Cannot specify both serial-port and address')
        return 1
    
    if args.address and not args.port:
        print('Specify port together with address')
        return 2

    conn = HanazederFP(serial_port=args.serial_port, address=args.address, port=args.port)
    conn.connect()
    value = conn.read_register(parser.register)
    print(f'Register {args.register} is {value}')
    return 0

if __name__ == '__main__':
    sys.exit(main())