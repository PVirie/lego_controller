from . import buwizz_3, transport
from .buwizz_3 import Buwizz_3_Ports, Buwizz_3_PU_Modes

async def scan():
    """
    Scan for BuWizz devices.
    """
    async for device in transport.scan():
        yield buwizz_3.Buwizz_3(device)