import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import lgpio
import atexit

# Define the GPIO pin to be used
INITIAL_PIN = 22

# Global variable to hold the GPIO chip handle
h = None

# Define the request model using Pydantic for validation
class PinTrigger(BaseModel):
    pin: int
    duration: float # Duration in seconds

def setup_gpio():
    """Initializes GPIO pin to a HIGH state on server startup."""
    global h
    try:
        h = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(h, INITIAL_PIN)
        lgpio.gpio_write(h, INITIAL_PIN, 0) # Set pin to LOW
        print(f"Pin {INITIAL_PIN} initialized to LOW.")
    except lgpio.error as e:
        print(f"GPIO setup error: {e}")
        if h:
            lgpio.gpiochip_close(h)
        h = None

def cleanup_gpio():
    """Cleans up GPIO resources on server shutdown."""
    if h:
        try:
            lgpio.gpio_write(h, INITIAL_PIN, 0) # Set pin to LOW
            lgpio.gpio_free(h, INITIAL_PIN)
            lgpio.gpiochip_close(h)
            print(f"Pin {INITIAL_PIN} has been cleaned up and GPIO chip is closed.")
        except lgpio.error as e:
            print(f"GPIO cleanup error: {e}")

app = FastAPI(
    title="Raspberry Pi GPIO Control API",
    description="An API to trigger GPIO pins on a Raspberry Pi 5.",
    version="1.0.0",
    on_startup=[setup_gpio],
    on_shutdown=[cleanup_gpio],
)

# In-memory lock to prevent concurrent access to the same pin
pin_locks = {}

@app.post("/trigger_pin/", summary="Trigger a GPIO pin")
async def trigger_pin(item: PinTrigger):
    """
    Triggers a specific GPIO pin by setting it to LOW for a given duration,
    then setting it back to HIGH.

    - **pin**: The GPIO pin number (BCM numbering).
    - **duration**: The time in seconds to keep the pin LOW.
    """
    if h is None:
        raise HTTPException(status_code=500, detail="GPIO chip not initialized.")

    if item.pin != INITIAL_PIN:
        raise HTTPException(status_code=400, detail=f"This server is configured to control pin {INITIAL_PIN} only.")

    if item.pin in pin_locks and not pin_locks[item.pin].done():
        raise HTTPException(status_code=409, detail=f"Pin {item.pin} is already in use.")

    lock = asyncio.Event()
    pin_locks[item.pin] = asyncio.create_task(lock.wait())

    try:
        # Set the pin to LOW
        lgpio.gpio_write(h, item.pin, 1)

        # Asynchronously wait for the specified duration
        await asyncio.sleep(item.duration)

        # Set the pin to HIGH
        lgpio.gpio_write(h, item.pin, 0)

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

