import os
import sys
import asyncio
import buwizz_interface as bwi
import signal
from datetime import datetime, timedelta

async def main():
    buwizz_interface = None
    async for device in bwi.scan():        
        buwizz_interface = device
        break

    if buwizz_interface is None:
        print('No BuWizz device found')
        return
    
    async def signal_handler(sig, frame):
        await buwizz_interface.exit()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    start_time = datetime.now()


    async for data in buwizz_interface():
        print(data)
        now_time = datetime.now()

        await buwizz_interface.set_powerup_motor_mode(mode='pwm')

        await buwizz_interface.set_motor_speed(0, 0.5)
        await buwizz_interface.set_motor_speed(1, 0.5)
        await buwizz_interface.set_motor_speed(2, 0.5)
        await buwizz_interface.set_motor_speed(3, 0.5)
        await buwizz_interface.set_motor_speed(4, 0.5)
        await buwizz_interface.set_motor_speed(5, 0.5)

        if now_time - start_time > timedelta(seconds=5):
            await buwizz_interface.exit()



if __name__ == '__main__':
    asyncio.run(main())