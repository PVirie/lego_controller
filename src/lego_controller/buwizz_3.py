from . import transport
import enum
from typing import Union
import logging
import struct

def put_to_byte(bytes, start, value):
    """
    Put a value in a byte array
    """
    for i in range(len(value)):
        bytes[start + i] = value[i]
    return bytes

class Buwizz_3_Ports(int, enum.Enum):
    PORT_1 = 0
    PORT_2 = 1
    PORT_3 = 2
    PORT_4 = 3
    PORT_A = 4
    PORT_B = 5


class Buwizz_3_PU_Modes(int, enum.Enum):
    DEFAULT = 1 # [-1, 1]
    PWM = 2 # [-1, 1]
    SPEED = 3 # [-1, 1] with PID
    POSITION = 4 # [-max int, max int] subtract from reference in degrees with PID
    ABSOLUTE = 5 # [-max int, max int] in degrees with PID

class Buwizz_3_Group_Modes(int, enum.Enum):
    NO_CHANGE = 6
    MOTOR = 7
    SERVO = 8


class Powerup_Motor_Status:
    def __init__(self, status_bytes, offset, mode):
        # Motor type (unsigned 8-bit),  
        # Velocity (signed 8-bit), 
        # Absolute position (unsigned 16-bit), 
        # Position (unsigned 32-bit) 

        self.motor_type = status_bytes[0]

        raw_speed = status_bytes[1]
        raw_abs_position = int.from_bytes(status_bytes[2:4], 'little')
        raw_position = int.from_bytes(status_bytes[4:8], 'little')
        
        self.abs_position = raw_abs_position
        if mode == Buwizz_3_PU_Modes.POSITION:
            self.position = raw_abs_position + offset
        else:
            self.position = raw_abs_position
        
        if mode == Buwizz_3_PU_Modes.SPEED:
            self.speed = raw_speed / 131 + offset
        else:
            self.speed = raw_speed / 131

class Buwizz_Status:
    def __init__(self, status_bytes, port_value_offsets, port_modes):
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
            Powerup_Motor_Status(status_bytes[22:30], port_value_offsets[0], port_modes[0]),
            Powerup_Motor_Status(status_bytes[30:38], port_value_offsets[1], port_modes[1]),
            Powerup_Motor_Status(status_bytes[38:46], port_value_offsets[2], port_modes[2]),
            Powerup_Motor_Status(status_bytes[46:54], port_value_offsets[3], port_modes[3])
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

        # create empty bytes (command byte will be added later)
        self.data_bytes = bytearray(20)
        self.port_mode_bytes = bytearray(4)
        self.port_PID_status_enable_bytes = bytearray(4)

        self.status_enabled = False
        self.port_current_pu_mode = [0] * 4 # NO MODE
        self.port_base_value = [0] * 4
        


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
        
        return Buwizz_Status(app_noti, self.port_base_value, self.port_current_pu_mode)


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
        if enable:
            self.port_PID_status_enable_bytes[port] = 1
        else:
            self.port_PID_status_enable_bytes[port] = 0

        await self.__send_command(b'\x51', bytes(self.port_PID_status_enable_bytes))
        

    async def set_powerup_motor_mode(self, port: Buwizz_3_Ports, mode: Union[Buwizz_3_PU_Modes, Buwizz_3_Group_Modes] = Buwizz_3_Group_Modes.NO_CHANGE, servo_ref=0):
        # set mode to PU
        # if mode is SPEED, accept servo reference in [-1, 1]
        # if mode is POSITION, accept servo reference in degrees [-max int, max int]
        # for the SPEED POSITION and ABSOLUTE mode, only work with PU L and PU XL motors
        
        if port >= 4:
            return
        
        current_port_mode = self.port_current_pu_mode[port]

        if current_port_mode == mode:
            return
        elif mode == Buwizz_3_Group_Modes.NO_CHANGE:
            return
        elif mode == Buwizz_3_Group_Modes.MOTOR:
            if current_port_mode == Buwizz_3_PU_Modes.SPEED or current_port_mode == Buwizz_3_PU_Modes.PWM or current_port_mode == Buwizz_3_PU_Modes.DEFAULT:
                return
            else:
                mode = Buwizz_3_PU_Modes.PWM
        elif mode == Buwizz_3_Group_Modes.SERVO:
            if current_port_mode == Buwizz_3_PU_Modes.POSITION or current_port_mode == Buwizz_3_PU_Modes.ABSOLUTE:
                return
            else:
                mode = Buwizz_3_PU_Modes.ABSOLUTE

        self.port_current_pu_mode[port] = mode

        if mode == Buwizz_3_PU_Modes.PWM:
            put_to_byte(self.port_mode_bytes, port, b'\x00')
        elif mode == Buwizz_3_PU_Modes.DEFAULT:
            put_to_byte(self.port_mode_bytes, port, b'\x10')
        elif mode == Buwizz_3_PU_Modes.SPEED:
            put_to_byte(self.port_mode_bytes, port, b'\x14')
        elif mode == Buwizz_3_PU_Modes.POSITION:
            # I override buwizz absolute position with mine
            # put_to_byte(self.port_mode_bytes, port, b'\x15')
            put_to_byte(self.port_mode_bytes, port, b'\x16')
        elif mode == Buwizz_3_PU_Modes.ABSOLUTE:
            put_to_byte(self.port_mode_bytes, port, b'\x16')

        await self.__send_command(b'\x50', bytes(self.port_mode_bytes))
        if mode == Buwizz_3_PU_Modes.POSITION:
            self.port_base_value[port] = servo_ref
        elif mode == Buwizz_3_PU_Modes.SPEED:
            self.port_base_value[port] = servo_ref
            

    async def set_motor_velocity(self, port: Buwizz_3_Ports, velocity: float):
        """
            input port: str, 1(power up), 2(power up), 3(power up), 4(power up), A(power function), B(power function)
            velocity is a float, -1.0 to 1.0
        """

        if port < 4:
            """
                bytes 1-16 is power up motors port 0 to 3, signed 32-bits for each, but we only use 8 bits: [-127, 127]
            """
            await self.set_powerup_motor_mode(port, Buwizz_3_Group_Modes.MOTOR)

            if self.port_current_pu_mode[port] == Buwizz_3_PU_Modes.POSITION:
                velocity = velocity - self.port_base_value[port]

            speed_raw = min(max(int((velocity + 1) * 255 / 2 - 127), -127), 127)
            put_to_byte(self.data_bytes, 4 * port, speed_raw.to_bytes(4, 'little', signed=True))
        elif port < 6:
            """
                bytes 17-18 is power function motors port 4 and 5, signed 8-bits for each
                    0x81 (-127): Full backwards
                    0x00 (0): Stop
                    0x7F (127): Full forwards
            """
            
            speed_raw = min(max(int((velocity + 1) * 255 / 2 - 127), -127), 127)
            put_to_byte(self.data_bytes, 16 + (port - 4), speed_raw.to_bytes(1, 'little', signed=True))

        # convert bytearray to bytes
        await self.__send_command(b'\x31', bytes(self.data_bytes))


    async def set_motor_angle(self, port: Buwizz_3_Ports, angle: float):
        """
            input port: str, 1(power up), 2(power up), 3(power up), 4(power up), A(power function), B(power function)
            angle is a float, -90.0 to 90.0, for power up motors, it is the angle in degrees
        """


        if port < 4:
            """
                bytes 1-16 is power up motors port 0 to 3, signed 32-bits for each
            """
            await self.set_powerup_motor_mode(port, Buwizz_3_Group_Modes.SERVO)

            if self.port_current_pu_mode[port] == Buwizz_3_PU_Modes.POSITION:
                angle = angle - self.port_base_value[port]

            put_to_byte(self.data_bytes, 4 * port, int(angle).to_bytes(4, 'little', signed=True))
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