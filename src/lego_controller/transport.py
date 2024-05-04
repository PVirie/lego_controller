import asyncio
from bleak import BleakScanner, BleakClient, BleakGATTCharacteristic
import logging
from async_property import async_property

# buwizz3 128-bit uuid is "93:6E:67:B1:19:99:B3:88:81:44:FB:74:D1:92:05:50"
# convert to python3 format by reversing order
BUWIZZ_3_UUID = "500592d1-74fb-4481-88b3-9919b1676e93"

async def scan(seconds=5):
    devices = await BleakScanner.discover(seconds)
    for d in devices:
        metadata_dict = d.metadata
        if "uuids" in metadata_dict and BUWIZZ_3_UUID in metadata_dict["uuids"]:
            yield d
        else:
            logging.info(f"Unknown device: {metadata_dict}")

"""
Application char UUID 0x2901 Write + Notify
Bootloader char UUID  0x8000 Write + Notify
UART ch. 1 char UUID  0x3901 Write + Notify
UART ch. 2 char UUID  0x3902 Write + Notify
UART ch. 3 char UUID  0x3903 Write + Notify
UART ch. 4 char UUID  0x3904 Write + Notify
"""

template = "5005{}-74fb-4481-88b3-9919b1676e93"
application_characteristic = "2901"
bootloader_characteristic = "8000"
uart_characteristic = ["3901", "3902", "3903", "3904"]

application_characteristic_uuid = template.format(application_characteristic)
bootloader_characteristic_uuid = template.format(bootloader_characteristic)
uart_characteristic_uuid = [template.format(u) for u in uart_characteristic]

class UART_Channels:
    def __init__(self, client):
        self.client = client

    async def __getitem__(self, key):
        return await self.client.read_gatt_char(uart_characteristic_uuid[key])
    
    async def __setitem__(self, key, value):
        await self.client.write_gatt_char(uart_characteristic_uuid[key], value)


class Transport:

    def __init__(self, device):
        self.device = device
        self.client = BleakClient(device.address)
        self.uart_channel = UART_Channels(self.client)

        self.app_notification = None
        self.boot_notification = None
        self.uart_notifications = [None, None, None, None]


    async def connect(self):
        await self.client.connect()

    async def disconnect(self):
        await self.client.disconnect()

    async def is_connected(self):
        return await self.client.is_connected()
    
    async def read_application(self):
        return await self.client.read_gatt_char(application_characteristic_uuid)
    
    async def read_bootloader(self):
        return await self.client.read_gatt_char(bootloader_characteristic_uuid)
    
    @property
    def uart(self):
        return self.uart_channel

    async def set_application(self, data):
        await self.client.write_gatt_char(application_characteristic_uuid, data)

    async def set_bootloader(self, data):
        await self.client.write_gatt_char(bootloader_characteristic_uuid, data)


    async def enable_application_notifications(self):
        await self.client.start_notify(application_characteristic_uuid, self._notification_handler)

    async def disable_application_notifications(self):
        await self.client.stop_notify(application_characteristic_uuid)

    async def enable_bootloader_notifications(self):
        await self.client.start_notify(bootloader_characteristic_uuid, self._notification_handler)

    async def disable_bootloader_notifications(self):
        await self.client.stop_notify(bootloader_characteristic_uuid)

    async def enable_uart_notifications(self, channel):
        await self.client.start_notify(uart_characteristic_uuid[channel], self._notification_handler)

    async def disable_uart_notifications(self, channel):
        await self.client.stop_notify(uart_characteristic_uuid[channel])


    async def _notification_handler(self, sender: BleakGATTCharacteristic, data: bytearray):
        # identify the sender
        if sender.uuid == application_characteristic_uuid:
            self.app_notification = data
        elif sender.uuid == bootloader_characteristic_uuid:
            self.boot_notification = data
        elif sender.uuid in uart_characteristic_uuid:
            index = uart_characteristic_uuid.index(sender.uuid)
            self.uart_notifications[index] = data
        else:
            logging.error(f"Unknown sender: {sender.uuid}")


    async def get_application_notification(self):
        return self.app_notification
    
    async def get_bootloader_notification(self):
        return self.boot_notification
    
    async def get_uart_notification(self, channel):
        return self.uart_notifications[channel]
    
        