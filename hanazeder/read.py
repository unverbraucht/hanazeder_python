import asyncio
from typing import List
from .Hanazeder import ConfigEntry, HanazederFP, SENSOR_LABELS
import argparse
import sys

class CliReader:
    sensor_val = None
    sensor_name = None
    sensor_custom_name = None
    sensor_idx = None

    def info_read(self, dev):
        print(f'Connected to {self.conn.device_type.name} with version {self.conn.version}')
    
    def sensor_read(self, idx: int, val: float):
        self.sensor_val = val
    
    def energy_read(self, energy):
        print('Energy readings:')
        print(f'  Total   {energy[0]}')
        print(f'  Current {energy[1]}')
        print(f'  Impulse {energy[2]}')
    
    def sensor_name_read(self, idx: int, name: str):
        self.sensor_custom_name = name

    def config_block_read(self, configs: List[ConfigEntry]):
        config_label = configs[self.sensor_idx]
        if config_label.value > 0:
            sensor_name = SENSOR_LABELS[config_label.value]

    async def main(self) -> int:
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

        self.conn = HanazederFP(debug=args.debug)
        await self.conn.open(serial_port=args.serial_port, address=args.address, port=args.port)
        await self.conn.read_information(self.info_read)
        await self.conn.wait_for_empty_queue()
        
        if args.energy:
            await self.conn.read_energy(self.energy_read)

        if args.sensor is not None:
            self.sensor_idx = args.sensor - 1

            print(f'Reading sensor {args.sensor}')
            await self.conn.read_sensor(self.sensor_idx, self.sensor_read)
            # Read label from fixed list
            await self.conn.read_config_block(27, 15, self.config_block_read)
            # Also read custom name
            await self.conn.read_sensor_name(self.sensor_idx, self.sensor_name_read)
        
        await self.conn.wait_for_empty_queue()
        print (f'Sensor {self.sensor_name if self.sensor_name else self.sensor_custom_name} ({self.sensor_idx}) has value {self.sensor_val}')
        return 0

if __name__ == '__main__':
    instance = CliReader()
    sys.exit(asyncio.run(instance.main())
)
