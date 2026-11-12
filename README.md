# Raspberry Pi GPIO Control API

A small FastAPI server for a Raspberry Pi 5 that sends a timed pulse on one GPIO pin. In the TPCAP Auto-ECAR system it is the **IO module** that resets a station PLC: `ecar_server` (`PlcService`) calls it on server start and at 07:15 and 12:50 every day.

- **Pin:** BCM **GPIO 22**, which is **physical pin 15** on the 40-pin header (nearest ground: pin 14)
- **Logic:** **active-HIGH**. The pin is LOW when idle and goes HIGH for `duration` seconds when triggered
- **Port:** HTTP `8000`

## How it works

### Startup

1. Opens GPIO chip 0 (`/dev/gpiochip0`) with `lgpio`.
2. Claims GPIO 22 as an output.
3. Sets GPIO 22 **LOW** (idle) and prints `Pin 22 initialized to LOW.`

If any of these steps fails, the server prints `GPIO setup error: ...` and keeps running, but `/trigger_pin/` returns `500 GPIO chip not initialized.` Fix the cause and restart the service.

### Triggering the pin

`POST /trigger_pin/` sets GPIO 22 **HIGH**, waits `duration` seconds (without blocking other requests), then sets it back **LOW**. The response is sent after the pulse has finished.

Only one pulse can run at a time. A request that arrives while a pulse is running gets `409` straight away; it is not queued.

### Shutdown

Sets GPIO 22 LOW, releases the pin and closes the GPIO chip.

### Why active-HIGH

At power-on GPIO 22 is an input with its internal pull-down, so it reads LOW. With LOW meaning "do nothing", the PLC is not reset while the Pi is booting or while the service is stopped. If you change the relay module, make sure it switches on a 3.3 V HIGH input.

## API

Base URL: `http://<pi-ip>:8000`. There is no authentication.

| Method | Path | Description |
|---|---|---|
| GET | `/` | Check that the server is running |
| POST | `/trigger_pin/` | Send one pulse on GPIO 22 |
| GET | `/docs` | Swagger UI (you can send test requests from the browser) |

### `POST /trigger_pin/`

Request body:

```json
{
  "pin": 22,
  "duration": 1.0
}
```

- `pin` (integer): BCM pin number. Must be `22`.
- `duration` (float): how long to hold the pin HIGH, in seconds. `ecar_server` sends `1.0`.

Response `200`:

```json
{
  "status": "success",
  "pin": 22,
  "duration": 1.0,
  "message": "Pin 22 was triggered for 1.0 seconds."
}
```

| Status | When |
|---|---|
| 200 | Pulse finished |
| 307 | Called `/trigger_pin` without the trailing slash; redirects to `/trigger_pin/` |
| 400 | `pin` is not 22 |
| 409 | A pulse is already running |
| 422 | Body is missing a field or has the wrong type |
| 500 | GPIO was not initialized at startup, or `lgpio` raised an error |

Example:

```bash
curl -X POST http://<pi-ip>:8000/trigger_pin/ \
  -H 'Content-Type: application/json' \
  -d '{"pin": 22, "duration": 1.0}'
```

Notes for callers:

- Set the client timeout to at least `duration + 2` seconds (3 s for the 1.0 s reset).
- `duration` is not range-checked. Do not send negative or very large values.
- Run only one uvicorn worker. Several workers would each try to claim GPIO 22, and the in-memory lock is not shared between them.

## Getting started

### Prerequisites

- Raspberry Pi 5 with Raspberry Pi OS Bookworm
- Python 3.9 or newer (Bookworm ships 3.11)
- The user that runs the service must be in the `gpio` group

### Installation

```bash
sudo apt update
sudo apt install -y git python3-venv python3-lgpio gpiod

git clone git@github.com:amrtdemdevteam/pi-server-control-gpio.git
cd pi-server-control-gpio

# --system-site-packages lets the venv use python3-lgpio from apt
python3 -m venv --system-site-packages venv
venv/bin/pip install -r requirements.txt
```

Check that GPIO 22 is on `gpiochip0` and is not used by another program:

```bash
gpioinfo | grep GPIO22
```

### Running the server manually

```bash
venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

You should see `Pin 22 initialized to LOW.`

## Running on startup (systemd)

1. Replace `<YOUR_USERNAME>` in `pi-server-control-gpio.service` with the user that owns the repository (for example `pi`). If the repository is not in that user's home directory, also update `WorkingDirectory` and `ExecStart`.

   ```bash
   sed -i "s/<YOUR_USERNAME>/$USER/g" pi-server-control-gpio.service
   ```

2. Install, enable and start the service:

   ```bash
   sudo cp pi-server-control-gpio.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now pi-server-control-gpio.service
   ```

3. Check the status and logs:

   ```bash
   systemctl status pi-server-control-gpio.service
   journalctl -u pi-server-control-gpio -f
   ```

### Updating

```bash
cd ~/pi-server-control-gpio
git pull
venv/bin/pip install -r requirements.txt
sudo systemctl restart pi-server-control-gpio
```

Avoid restarting around 07:15 and 12:50, when `ecar_server` sends its scheduled resets.

## Wiring

| Signal | Header pin |
|---|---|
| GPIO 22 (output) | 15 |
| Ground | 14 |

A GPIO pin gives 3.3 V and only a few mA, so drive the PLC reset input through a relay module (or optocoupler/SSR) that accepts a 3.3 V active-HIGH input. Never connect 5 V or 24 V to the GPIO pin.

## Registering the Pi in ecar_server

`ecar_server` finds each station's IO module in the `optionalIo` field of the station document (database `tpcap-ecar`, collection `stations`):

```js
{ optionalIo: { ip: "192.168.50.X", port: 8000, type: "pi5", description: "PLC reset BODY" } }
```

Stop `ecar_server` before editing this field, because it writes station state back to MongoDB every 3 seconds. When it starts again it sends a reset to every IO module after about 2 seconds, which is a quick way to test the connection.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `500 GPIO chip not initialized.` | User not in the `gpio` group, another program holds GPIO 22, or the header is not on `gpiochip0` (older kernels). Check `journalctl`, fix, then restart the service. |
| Service fails to start | `<YOUR_USERNAME>` not replaced, `venv/` missing, or `lgpio` not importable in the venv |
| Frequent `409` | Two stations point to the same Pi and are triggered together, or the caller retries before the pulse ends |
| `200` but the PLC does not reset | Wrong header pin, loose wire, or the relay module is active-LOW or does not switch at 3.3 V |

## License

MIT. See [LICENSE](LICENSE).
