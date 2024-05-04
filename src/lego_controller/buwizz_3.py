from . import transport
import enum
from typing import Union
import struct

def put_to_byte(bytes, start, value):
    """
    Put a value in a byte array
    """
    for i in range(len(value)):
        bytes[start + i] = value[i]
    return bytes

class Buwizz_3_Ports(enum.Enum):
    PORT_1 = 0
    PORT_2 = 1
    PORT_3 = 2
    PORT_4 = 3
    PORT_A = 4
    PORT_B = 5


class Buwizz_3_PU_Modes(enum.Enum):
    DEFAULT = 0 # [-127, 128]
    PWM = 1 # [-127, 128]
    SPEED = 2
    POSITION = 3
    ABSOLUTE = 4

class Powerup_Motor_Status:
    def __init__(self, status_bytes):
        # Motor type (unsigned 8-bit),  
        # Velocity (signed 8-bit), 
        # Absolute position (unsigned 16-bit), 
        # Position (unsigned 32-bit) 

        self.motor_type = status_bytes[0]
        self.velocity = status_bytes[1]
        self.abs_position = int.from_bytes(status_bytes[2:4], 'little')
        self.position = int.from_bytes(status_bytes[4:8], 'little')

class Buwizz_Status:
    def __init__(self, status_bytes):
        # status byte is byte 1

        status_byte = status_bytes[1]

        self.error = status_byte & 0x01
        self.motion_wakeup_enable = (status_byte & 0x02) >> 1
        self.ble_longrange_enable = (status_byte & 0x04) >> 2
        self.charging = (status_byte & 0x20) >> 6
        self.usb_connecting = (status_byte & 0x40) >> 7

        # bit 3 and 4, for 2 bits of 4 levels
        self.battery_level = (status_byte & 0x18) >> 3 
        self.battery_charge_current = status_bytes[21]

        # 9 + value*0.05
        self.voltage = 9 + status_bytes[2] * 0.05

        self.temperature = status_bytes[9] 

        # acceleration x: 10-11, y: 12-13, z: 14-15;  0.488 mg/LSB
        self.acc_x = int.from_bytes(status_bytes[10:12], 'little', signed=True) * 0.488
        self.acc_y = int.from_bytes(status_bytes[12:14], 'little', signed=True) * 0.488
        self.acc_z = int.from_bytes(status_bytes[14:16], 'little', signed=True) * 0.488

        # bytes 22-53
        self.powerup_motor_statuses = [
            Powerup_Motor_Status(status_bytes[22:30]),
            Powerup_Motor_Status(status_bytes[30:38]),
            Powerup_Motor_Status(status_bytes[38:46]),
            Powerup_Motor_Status(status_bytes[46:54])
        ]

    def __str__(self):
        return f"""
        Error: {self.error}
        Motion Wakeup Enable: {self.motion_wakeup_enable}
        BLE Longrange Enable: {self.ble_longrange_enable}
        Charging: {self.charging}
        USB Connecting: {self.usb_connecting}
        Battery Level: {self.battery_level}
        Battery Charge Current: {self.battery_charge_current}
        Voltage: {self.voltage}
        Temperature: {self.temperature}
        Acceleration:
            x: {self.acc_x}
            y: {self.acc_y}
            z: {self.acc_z}
        Powerup Motor Statuses:
            {self.powerup_motor_statuses[0].__dict__}
            {self.powerup_motor_statuses[1].__dict__}
            {self.powerup_motor_statuses[2].__dict__}
            {self.powerup_motor_statuses[3].__dict__}
        """


PF_SERVO_POSSIBLE_VALUES=[
    int(-127).to_bytes(1, 'little', signed=True),
    int(0).to_bytes(1, 'little', signed=True),
    int(127).to_bytes(1, 'little', signed=True)
]

class Buwizz_3:

    def __init__(self, device):
        self.transport = transport.Transport(device)

        # create empty bytes of 20 bytes (command byte will be added later)
        self.data_bytes = bytearray(20)
        self.status_enabled = False

        self.port_current_pu_mode = [Buwizz_3_PU_Modes.PWM] * 4
        self.port_mode_bytes = bytearray(4)
        self.port_ref_bytes = bytearray(16)

        self.port_PID_status_enable_bytes = bytearray(4)

    async def exit(self):
        await self.transport.disconnect()


    async def is_connected(self):
        return await self.transport.is_connected()


    async def start(self):
        await self.transport.connect()


    async def get_status(self):
        app_noti = await self.transport.get_application_notification()
        if app_noti is None:
            return None
        
        return Buwizz_Status(app_noti)


    async def __send_command(self, command, data):
        # from bytesm, command is the first byte, the rest is data
        await self.transport.set_application(command + data)


    async def set_data_refresh_rate(self, rate):
        """
            rate from 20*5 to 255*5 ms, (valid range: 20 - 255) in steps of 5 ms
        """
        if rate <= 0:
            await self.transport.disable_application_notifications()
            self.status_enabled = False
            return

        if not self.status_enabled:
            await self.transport.enable_application_notifications()
            self.status_enabled = True

        raw_rate = int(min(max(rate, 100), 1275))//5
        await self.__send_command(b'\x32', raw_rate.to_bytes(1, 'little'))


    async def set_powerup_motor_PID_status_enable(self, port: Buwizz_3_Ports, enable: bool):
        port = port.value
        if enable:
            self.port_PID_status_enable_bytes[port] = 1
        else:
            self.port_PID_status_enable_bytes[port] = 0

        await self.__send_command(b'\x51', bytes(self.port_PID_status_enable_bytes))
        

    async def set_powerup_motor_mode(self, port: Buwizz_3_Ports, mode:Buwizz_3_PU_Modes = Buwizz_3_PU_Modes.DEFAULT, servo_ref=0):
        # set mode to PU simple PWM (default)
        # if mode is speed or position, set servo reference convert input -1 to 1 to signed 32 bits
        # for the SPEED POSITION and ABSOLUTE mode, only work with PU L and PU XL motors
        
        port = port.value
        if port >= 4:
            return
        
        if self.port_current_pu_mode[port] == mode:
            return
        
        self.port_current_pu_mode[port] = mode

        if mode == Buwizz_3_PU_Modes.PWM:
            put_to_byte(self.port_mode_bytes, port, b'\x00')
        elif mode == Buwizz_3_PU_Modes.DEFAULT:
            put_to_byte(self.port_mode_bytes, port, b'\x10')
        elif mode == Buwizz_3_PU_Modes.SPEED:
            put_to_byte(self.port_mode_bytes, port, b'\x14')
        elif mode == Buwizz_3_PU_Modes.POSITION:
            put_to_byte(self.port_mode_bytes, port, b'\x15')
        elif mode == Buwizz_3_PU_Modes.ABSOLUTE:
            put_to_byte(self.port_mode_bytes, port, b'\x16')

        await self.__send_command(b'\x50', bytes(self.port_mode_bytes))
        if mode == Buwizz_3_PU_Modes.SPEED or mode == Buwizz_3_PU_Modes.POSITION:
            ref_bytes = int(servo_ref * 2147483647).to_bytes(4, 'little', signed=True)
            put_to_byte(self.port_ref_bytes, port*4, ref_bytes)
            await self.__send_command(b'\x52', bytes(self.port_ref_bytes))
            


    async def set_motor_speed(self, port: Buwizz_3_Ports, speed: float):
        """
            input port: str, 1(power up), 2(power up), 3(power up), 4(power up), A(power function), B(power function)
            speed is a float, -1.0 to 1.0
        """
        port = port.value

        if port < 4:
            """
                bytes 1-16 is power up motors port 0 to 3, signed 32-bits for each, but we only use 8 bits: [-127, 128]
            """
            self.set_powerup_motor_mode(port, Buwizz_3_PU_Modes.DEFAULT)
            put_to_byte(self.data_bytes, 4 * port, int(speed * 127).to_bytes(4, 'little', signed=True))
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


    async def set_motor_angle(self, port: Buwizz_3_Ports, angle: float):
        """
            input port: str, 1(power up), 2(power up), 3(power up), 4(power up), A(power function), B(power function)
            speed is a float, -90.0 to 90.0
        """
        port = port.value


        if port < 4:
            """
                bytes 1-16 is power up motors port 0 to 3, signed 32-bits for each
            """
            self.set_powerup_motor_mode(port, Buwizz_3_PU_Modes.ABSOLUTE)
            # interpolate speed to int 32 bits -1 is min int value, 1 is max int value
            put_to_byte(self.data_bytes, 4 * port, int((angle / 90) * 2147483647).to_bytes(4, 'little', signed=True))
        elif port < 6:
            """
                bytes 17-18 is power function motors port 4 and 5, signed 8-bits for each
                    0x81 (-127): PF servo left 
                    0x00 (0): PF servo center
                    0x7F (127): PF servo right
                    Do not use in between values, as the servo will not move
            """
            put_to_byte(self.data_bytes, 16 + (port - 4), PF_SERVO_POSSIBLE_VALUES[min(max(round(angle / 90), -1), 1) + 1])

        # convert bytearray to bytes
        await self.__send_command(b'\x31', bytes(self.data_bytes))


    async def break_motors(self, port):
        """
            input port: int, 0-5
            byte 19 Brake flags - bit mapped to bits 5-0 (1 bit per each motor, bit 0 for first motor, bit 5 for the last)
        """


        # set bit 0 to 1
        self.data_bytes[19] = 1 << port

        await self.__send_command(b'\x31', bytes(self.data_bytes))



    async def activate_shelf_mode(self):
        """
            For long term hibernation, the operator will have to connect charger to wake up the device. 
        """
        await self.transport.set_application(b'\xA1')