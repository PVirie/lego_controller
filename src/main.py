import os
import sys
import asyncio
import buwizz_interface
import signal

async def main():
    buwizz_interface = None
    async for device in buwizz_interface.scan():        
        buwizz_interface = device
        break

    if buwizz_interface is None:
        print('No BuWizz device found')
        return
    
    async def signal_handler(sig, frame):
        await buwizz_interface.exit()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    for data in buwizz_interface():
        print(data)
        await asyncio.sleep(3)
        
        await buwizz_interface.set_motor_speed(0, 0.5)
        await buwizz_interface.set_motor_speed(1, 0.5)
        await buwizz_interface.set_motor_speed(2, 0.5)
        await buwizz_interface.set_motor_speed(3, 0.5)
        await buwizz_interface.set_motor_speed(4, 0.5)
        await buwizz_interface.set_motor_speed(5, 0.5)

        await asyncio.sleep(3)
        
        await buwizz_interface.set_motor_speed(0, 0.0)
        await buwizz_interface.set_motor_speed(1, 0.0)
        await buwizz_interface.set_motor_speed(2, 0.0)
        await buwizz_interface.set_motor_speed(3, 0.0)
        await buwizz_interface.set_motor_speed(4, 0.0)
        await buwizz_interface.set_motor_speed(5, 0.0)


if __name__ == '__main__':
    asyncio.run(main())