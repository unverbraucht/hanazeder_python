from .Hanazeder import HanazederFP, SENSOR_LABELS
import argparse
import sys

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial-port", help="set serial port",
                    type=str)
    parser.add_argument("--sensor", help="sensor to read",
                    type=int)
    parser.add_argument("--energy", help="read energy values", action="store_true")
    parser.add_argument("--debug", help="print low-level messages", action="store_true")
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
    if not args.sensor and not args.energy:
        print("Don't know what to do, please add --energy and/or --sensor")

    conn = HanazederFP(serial_port=args.serial_port, address=args.address, port=args.port, debug=args.debug)
    conn.read_information()
    print(f'Connected to {conn.device_type.name} with version {conn.version}')

    if args.sensor is not None:
        sensor_idx = args.sensor - 1
        print(f'Reading sensor {args.sensor}')
        value = conn.read_sensor(sensor_idx)
        # Read label from fixed list
        name = None
        configs = conn.read_config_block(27, 15)
        config_label = configs[sensor_idx]
        if config_label.value > 0:
            name = SENSOR_LABELS[config_label.value]
        else:
            # Read label from device
            name = conn.read_sensor_name(sensor_idx)

        # idx = 0
        # for config in configs:
        #     idx = idx + 1
        #     if config.value > 0:
        #         print(f'Label {idx} is {SENSOR_LABELS[config.value]}')
        
        print(f'Sensor {name} ({args.sensor}) is {value}')

    if args.energy:
        energy = conn.read_energy()
        print('Energy readings:')
        print(f'  Total   {energy[0]}')
        print(f'  Current {energy[1]}')
        print(f'  Impulse {energy[2]}')
    return 0

if __name__ == '__main__':
    sys.exit(main())