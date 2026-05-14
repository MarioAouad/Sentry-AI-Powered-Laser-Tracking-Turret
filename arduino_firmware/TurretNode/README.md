# TurretNode Sketch

Arduino sketch folder for the ESP32 actuator node.

## Build Inputs

- `TurretNode.ino`: main sketch.
- `Config.h`: hardware pins, baud rate, servo limits, and deadband.
- `SerialParser.*`: parses `pan,tilt,state` commands.
- `ServoControl.*`: writes bounded servo commands.
- `Payload.*`: controls laser and LEDs.

## Before Upload

1. Check pin assignments in `Config.h`.
2. Confirm `BAUD_RATE` matches the Python config.
3. Confirm servo min/max angle limits match the physical mount.
4. Install the `ESP32Servo` Arduino library.

The sketch expects commands from `python_vision/src/comms/serial_tether.py`.
