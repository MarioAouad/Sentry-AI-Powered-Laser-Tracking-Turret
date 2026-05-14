# Communications Module

Serial transport from the Python vision backend to the ESP32 actuator firmware.

## File

- `serial_tether.py`: serial connection management, reconnect behavior, and command queue.

## Command Format

```text
pan,tilt,state\n
```

The ESP32 firmware parses the same format in `arduino_firmware/TurretNode/SerialParser.*`.

## States

- `STATE_OFF`
- `STATE_SCANNING`
- `STATE_LOCKED`

Keep the baud rate aligned with `python_vision/config/hardware_offsets.yaml` and `arduino_firmware/TurretNode/Config.h`.
