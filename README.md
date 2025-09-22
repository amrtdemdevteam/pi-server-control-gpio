# Raspberry Pi GPIO Control API

This project provides a simple and efficient FastAPI-based server to control a GPIO pin on a Raspberry Pi 5. It is specifically configured to manage **pin 17**.

## Features

- **FastAPI Backend**: A modern, fast (high-performance) web framework for building APIs with Python.
- **GPIO Control**: Exposes a single endpoint to trigger a GPIO pin.
- **Startup Initialization**: Automatically initializes GPIO pin 17 to a **HIGH** logic level when the server starts.
- **Graceful Shutdown**: Cleans up GPIO resources and sets pin 17 to **LOW** when the server shuts down.
- **Concurrent Request Handling**: Includes a locking mechanism to prevent multiple requests from accessing the pin simultaneously.

## How It Works

### Server Startup

When the server starts, it performs the following actions:
1.  Opens a connection to the GPIO chip.
2.  Claims GPIO pin 17 as an output.
3.  Sets pin 17 to a **HIGH** state.

This ensures that the connected device is in a known, default state as soon as the application is running.

### Triggering the Pin

The API exposes a single endpoint, `/trigger_pin/`, that allows you to temporarily set the pin to **LOW**.

- **Endpoint**: `POST /trigger_pin/`
- **Request Body**:
  ```json
  {
    "pin": 17,
    "duration": 1.5
  }
  ```
  - `pin` (integer): The pin to trigger. Must be `17`.
  - `duration` (float): The time in seconds to keep the pin in the LOW state.

When a request is received, the server sets pin 17 to **LOW** for the specified duration and then returns it to its default **HIGH** state.

### Server Shutdown

On shutdown, the server will automatically set pin 17 back to **LOW** and release all GPIO resources.

## Getting Started

### Prerequisites

- A Raspberry Pi 5 with Raspberry Pi OS.
- Python 3.7+ installed.
- `lgpio` library, which is typically pre-installed on modern Raspberry Pi OS images.

### Installation

1.  **Clone the repository**:
    ```bash
    git clone <your-repository-url>
    cd pi-server-control-gpio
    ```

2.  **Create a `requirements.txt` file**:
    ```
    fastapi
    uvicorn[standard]
    lgpio
    ```

3.  **Install the dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### Running the Server

To run the API server, execute the following command in your terminal:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

- `--host 0.0.0.0`: Makes the server accessible from other devices on your network.
- `--port 8000`: Runs the server on port 8000.

You should see output indicating that pin 17 has been initialized to HIGH.

## API Documentation

Once the server is running, you can access the interactive API documentation (provided by Swagger UI) by navigating to:

[http://<your-pi-ip-address>:8000/docs](http://<your-pi-ip-address>:8000/docs)

From there, you can test the `/trigger_pin/` endpoint directly from your browser.
