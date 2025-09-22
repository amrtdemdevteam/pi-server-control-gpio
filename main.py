import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import lgpio

# Define the request model using Pydantic for validation
class PinTrigger(BaseModel):
    pin: int
    duration: float # Duration in seconds

app = FastAPI(
    title="Raspberry Pi GPIO Control API",
    description="An API to trigger GPIO pins on a Raspberry Pi 5.",
    version="1.0.0",
)

# In-memory lock to prevent concurrent access to the same pin
pin_locks = {}

@app.post("/trigger_pin/", summary="Trigger a GPIO pin")
async def trigger_pin(item: PinTrigger):
    """
    Triggers a specific GPIO pin by setting it to HIGH for a given duration,
    then setting it back to LOW.

    - **pin**: The GPIO pin number (BCM numbering).
    - **duration**: The time in seconds to keep the pin HIGH.
    """
    if item.pin in pin_locks and not pin_locks[item.pin].done():
        raise HTTPException(status_code=409, detail=f"Pin {item.pin} is already in use.")

    lock = asyncio.Event()
    pin_locks[item.pin] = asyncio.create_task(lock.wait())

    try:
        # Open the default GPIO chip (chip 0)
        h = lgpio.gpiochip_open(0)

        # Claim the GPIO pin for output
        lgpio.gpio_claim_output(h, item.pin)

        try:
            # Set the pin to HIGH
            lgpio.gpio_write(h, item.pin, 0)

            # Asynchronously wait for the specified duration
            await asyncio.sleep(item.duration)

            # Set the pin to LOW
            lgpio.gpio_write(h, item.pin, 1)

        finally:
            # Always release the pin
            lgpio.gpio_free(h, item.pin)
            # Close the chip handle
            lgpio.gpiochip_close(h)

    except lgpio.error as e:
        raise HTTPException(status_code=500, detail=f"GPIO error: {e}")
    finally:
        # Release the lock
        lock.set()
        del pin_locks[item.pin]

    return {
        "status": "success",
        "pin": item.pin,
        "duration": item.duration,
        "message": f"Pin {item.pin} was triggered for {item.duration} seconds."
    }

@app.get("/", summary="Root endpoint")
def read_root():
    """
    A simple root endpoint to confirm the server is running.
    """
    return {"message": "Welcome to the Raspberry Pi GPIO Control API. See /docs for more info."}

# To run this application:
# 1. Install dependencies: pip install -r requirements.txt
# 2. Run the server: uvicorn main:app --host 0.0.0.0 --port 8000
