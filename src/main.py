import os
import sys
import asyncio
import buwizz_interface as bwi
import signal
from datetime import datetime, timedelta
import random

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

    await buwizz_interface.start()

    await buwizz_interface.set_powerup_motor_mode(bwi.Buwizz_3_Ports.PORT_1, mode=bwi.Buwizz_3_PU_Modes.DEFAULT, servo_ref=0)
    await buwizz_interface.set_powerup_motor_mode(bwi.Buwizz_3_Ports.PORT_2, mode=bwi.Buwizz_3_PU_Modes.DEFAULT, servo_ref=0)
    await buwizz_interface.set_powerup_motor_mode(bwi.Buwizz_3_Ports.PORT_3, mode=bwi.Buwizz_3_PU_Modes.DEFAULT, servo_ref=0)
    await buwizz_interface.set_powerup_motor_mode(bwi.Buwizz_3_Ports.PORT_4, mode=bwi.Buwizz_3_PU_Modes.DEFAULT, servo_ref=0)

    await buwizz_interface.set_data_refresh_rate(100)
    
    start_time = datetime.now()

    while True:
        now_time = datetime.now()

        status = await buwizz_interface.get_status()
        print(status)

        await buwizz_interface.set_motor_speed(bwi.Buwizz_3_Ports.PORT_1, 0)
        await buwizz_interface.set_motor_speed(bwi.Buwizz_3_Ports.PORT_2, 0)
        await buwizz_interface.set_motor_speed(bwi.Buwizz_3_Ports.PORT_3, 0)
        await buwizz_interface.set_motor_speed(bwi.Buwizz_3_Ports.PORT_4, 0.5)
        await buwizz_interface.set_motor_speed(bwi.Buwizz_3_Ports.PORT_A, 1)
        await buwizz_interface.set_motor_speed(bwi.Buwizz_3_Ports.PORT_B, 1)

        if now_time - start_time > timedelta(seconds=10):
            await buwizz_interface.exit()
            break



if __name__ == '__main__':
    asyncio.run(main())