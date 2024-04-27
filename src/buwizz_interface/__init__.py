from . import buwizz_3, transport

async def scan():
    """
    Scan for BuWizz devices.
    """
    async for device in transport.scan():
        yield buwizz_3.Buwizz_3(device)