from . import transport


def put_to_byte(bytes, start, value):
    """
    Put a value in a byte array
    """
    for i in range(len(value)):
        bytes[start + i] = value[i]
    return bytes

class Buwizz_3:

    def __init__(self, device):
        self.transport = transport.Transport(device)

        # create empty bytes of 20 bytes (command byte will be added later)
        self.data_bytes = bytearray(20)

        self.powerup_mode = 'pwm'

    async def exit(self):
        await self.transport.disconnect()

    async def __call__(self):
        await self.transport.connect()
        while await self.transport.is_connected():
            all_notifications = await self.transport.get_all_notifications()

            # interpret notifications and return

            yield 

    async def __send_command(self, command, data):
        # from bytesm, command is the first byte, the rest is data
        await self.transport.set_application(command + data)


    async def set_powerup_motor_mode(self, mode='pwm'):
        # set mode to PU simple PWM (default)
        if mode != self.powerup_mode:
            self.powerup_mode = mode
            if mode == 'pwm':
                await self.__send_command(b'\x50', b'\x00')


    async def set_motor_speed(self, port, speed: float):
        """
        input port: int, 0-5
        speed is a float, -1.0 to 1.0
        """

        if port < 4:
            """
                bytes 1-16 is power up motors port 0 to 3, signed 32-bits for each
            """
            # interpolate speed to int 32 bits -1 is min int value, 1 is max int value
            speed = int(speed * 2147483647)

            # now put speed in the correct byte position
            put_to_byte(self.data_bytes, 4 * port, speed.to_bytes(4, 'little', signed=True))

        elif port < 6:
            """
                bytes 17-18 is power function motors port 4 and 5, signed 8-bits for each
                    0x81 (-127): Full backwards
                    0x00 (0): Stop
                    0x7F (127): Full forwards
            """
            # interpolate speed to 1 byte -127 is min int value, 127 is max int value
            put_to_byte(self.data_bytes, 16 + (port - 4), int(speed * 127).to_bytes(1, 'little', signed=True))

        # convert bytearray to bytes
        await self.__send_command(b'\x31', bytes(self.data_bytes))



    async def break_motors(self, port):
        """
        input port: int, 0-5
        byte 19 Brake flags - bit mapped to bits 5-0 (1 bit per each motor, bit 0 for first motor, bit 5
        for the last)
        """


        # set bit 0 to 1
        self.data_bytes[19] = 1 << port

        await self.__send_command(b'\x31', bytes(self.data_bytes))