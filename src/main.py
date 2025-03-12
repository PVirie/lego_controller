import asyncio
import lego_controller as lc
import signal
import keyboard


async def control_logic(state, keyboard):
    # you can implement any logic here

    action_1 = 0
    if keyboard.is_pressed("q"):
        action_1 = 1
    elif keyboard.is_pressed("a"):
        action_1 = -1
    
    action_2 = 0
    if keyboard.is_pressed("e"):
        action_2 = 1
    elif keyboard.is_pressed("d"):
        action_2 = -1

    action_3 = 0
    if keyboard.is_pressed("up"):
        action_3 = 90
    elif keyboard.is_pressed("down"):
        action_3 = -90

    action_4 = 0
    if keyboard.is_pressed("right"):
        action_4 = 90
    elif keyboard.is_pressed("left"):
        action_4 = -90

    return action_1, action_2, action_3, action_4, 0, 0


async def main():
    buwizz_interface = None
    async for device in lc.scan():        
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
    await buwizz_interface.set_data_refresh_rate(100)
    
    # set up servo motors
    await buwizz_interface.set_powerup_motor_mode(lc.Buwizz_3_Ports.PORT_3, lc.Buwizz_3_PU_Modes.POSITION, 0)
    await buwizz_interface.set_powerup_motor_mode(lc.Buwizz_3_Ports.PORT_4, lc.Buwizz_3_PU_Modes.POSITION, -90)

    while True:
        status = await buwizz_interface.get_status()
        print(status, end='\r')

        # control logic
        actions = await control_logic(status, keyboard)

        # write arrow keys to control the motors
        await buwizz_interface.set_motor_velocity(lc.Buwizz_3_Ports.PORT_1, actions[0])
        await buwizz_interface.set_motor_velocity(lc.Buwizz_3_Ports.PORT_2, actions[1])
        await buwizz_interface.set_motor_angle(lc.Buwizz_3_Ports.PORT_3, actions[2])
        await buwizz_interface.set_motor_angle(lc.Buwizz_3_Ports.PORT_4, actions[3])

        # # Power up servo modes
        # await buwizz_interface.set_motor_angle(lc.Buwizz_3_Ports.PORT_1, 90)
        # await buwizz_interface.set_motor_angle(lc.Buwizz_3_Ports.PORT_2, 180)

        # # Power up speed modes
        # await buwizz_interface.set_motor_velocity(lc.Buwizz_3_Ports.PORT_3, 1)
        # await buwizz_interface.set_motor_velocity(lc.Buwizz_3_Ports.PORT_4, -1)
        
        # # Power function servo modes
        # await buwizz_interface.set_motor_angle(lc.Buwizz_3_Ports.PORT_A, -90)

        # # Power function speed modes
        # await buwizz_interface.set_motor_velocity(lc.Buwizz_3_Ports.PORT_B, 1)

        if keyboard.is_pressed('esc'):
            await buwizz_interface.exit()
            break

        if keyboard.is_pressed('f12'):
            await buwizz_interface.activate_shelf_mode()
            print('Shelf mode activated')
            break


if __name__ == '__main__':
    asyncio.run(main())