import asyncio
from typing import List
from .Hanazeder import ConfigEntry, HanazederFP, SENSOR_LABELS
import argparse
import sys
import logging

FORMAT = '%(asctime)s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)

class CliReader:
    sensor_vals = [None] * 15
    sensor_names = [None] * 15
    sensor_custom_name = None
    sensor_idx = None

    def config_block_read(self, configs: List[ConfigEntry]):
        for i, config_label in enumerate(configs):
            if config_label.value > 0:
                self.sensor_names[i] = SENSOR_LABELS[config_label.value]

    def print_sensor(self, i):
        print (f'Sensor {self.sensor_names[i]} ({i}) has value {self.sensor_vals[i]}')
    
    async def get_sensor_name(self, i):
        return self.sensor_names[i]

    async def main(self) -> int:
        parser = argparse.ArgumentParser()
        parser.add_argument("--serial-port", help="set serial port",
                        type=str)
        parser.add_argument("--sensor", help="sensor to read",
                        type=int)
        parser.add_argument("--sensors", help="read all sensors", action="store_true")
        parser.add_argument("--energy", help="read energy values", action="store_true")
        parser.add_argument("--outlets", help="read outlet/pump values", action="store_true")
        parser.add_argument("--loop", help="read values in a loop", action="store_true")
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
        if not args.sensor and not args.energy and not args.sensors and not args.outlets:
            print("Don't know what to do, please add --energy, --outlets, --sensors and/or --sensor")

        self.conn = HanazederFP(debug=args.debug, request_timeout=2)
        await self.conn.open(serial_port=args.serial_port, address=args.address, port=args.port, timeout=0.2)
        await self.conn.read_information()
        print(f'Connected to {self.conn.device_type.name} with version {self.conn.version}')

        loop_count = 1000 if args.loop else 1
        
        async def dummy():
            return None
        
        while loop_count > 0:
            loop_count = loop_count - 1
            if args.outlets:
                outlets = await self.conn.read_outlets()
                print(f'Outlet states: {outlets}')
            if args.energy:
                energy = await self.conn.read_energy()
                print('Energy readings:')
                print(f'  Total   {energy[0]}')
                print(f'  Current {energy[1]}')
                print(f'  Impulse {energy[2]}')

            if args.sensors:
                # Read label from fixed list
                name_tasks = []
                
                self.config_block_read(await self.conn.read_config_block(27, 15))
                for i in range(0, 15):
                    # Also read custom name
                    if self.sensor_names[i] is None:
                        self.sensor_names[i] = await self.conn.read_sensor_name(i)
                    #else:
                    #    values_tasks.append(self.get_sensor_name(i))
                values_tasks = []
                for i in range(0, 15):
                    values_tasks.append(self.conn.read_sensor(i))
                
                self.sensor_vals = await asyncio.gather(*values_tasks)
                
                for i in range(0, 15):
                    self.print_sensor(i)
            elif args.sensor is not None:
                self.sensor_idx = args.sensor - 1

                print(f'Reading sensor {args.sensor}')
                self.sensor_vals[self.sensor_idx] = await self.conn.read_sensor(self.sensor_idx)
                # Read label from fixed list
                self.config_block_read(await self.conn.read_config_block(27, 15))
                # Also read custom name
                if self.sensor_names[self.sensor_idx] is None:
                    self.sensor_names[self.sensor_idx] = await self.conn.read_sensor_name(self.sensor_idx)
                self.print_sensor(self.sensor_idx)
                
        return 0

if __name__ == '__main__':
    instance = CliReader()
    sys.exit(asyncio.run(instance.main(), debug=True)
)
