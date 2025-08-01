import asyncio
import random
from bleak import BleakServer  # This does NOT exist! Just simulating logic here

# This is not real. Just for mocking logic.
class MockBLEPeripheral:
    def __init__(self, uuid):
        self.uuid = uuid

    async def start(self):
        while True:
            await asyncio.sleep(2)
            msg = random.choice(["OK", "ScrollLoose", "ViolinTilted", f"Height:{random.randint(10, 20)}"])
            print(f"Sending BLE message: {msg}")
            # You would trigger the callback here in real hardware
            # Not needed now — just simulates BLE activity.

asyncio.run(MockBLEPeripheral("cba1d466-344c-4be3-ab3f-189f80dd7518").start())
