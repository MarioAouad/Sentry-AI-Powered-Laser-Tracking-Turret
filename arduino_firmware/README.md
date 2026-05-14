# ESP32 Turret Firmware

Firmware for the actuator node. The ESP32 does not run computer vision; it receives serial commands from the Python vision process and converts them into servo and payload outputs.

## Hardware Role

- Drive two SG90 servos for pan and tilt.
- Toggle the laser payload when the Python pipeline reports a lock.
- Show status through LEDs.
- Keep motion logic simple and low latency.

## Serial Command Contract

The Python process sends one newline-terminated command:

```text
pan,tilt,state\n
```

- `pan`: servo angle in degrees.
- `tilt`: servo angle in degrees.
- `state`: integer state flag.

State values are defined in both the Python serial tether and firmware configuration:

- `0`: off/safe
- `1`: scanning
- `2`: locked

## Main Files

- `TurretNode/TurretNode.ino`: setup and main loop.
- `TurretNode/Config.h`: pins, baud rate, angle limits, and deadband.
- `TurretNode/SerialParser.*`: parses serial commands.
- `TurretNode/ServoControl.*`: applies safe servo angles.
- `TurretNode/Payload.*`: controls laser and status LEDs.

## Flashing

1. Open `TurretNode/TurretNode.ino` in the Arduino IDE.
2. Install the `ESP32Servo` library.
3. Install the Espressif ESP32 board package.
4. Select the correct ESP32 board.
5. Check all pin assignments in `Config.h`.
6. Confirm the baud rate matches `python_vision/config/hardware_offsets.yaml`.
7. Compile and upload.

After flashing, connect the ESP32 serial port to the computer running `python_vision/main_orchestrator.py`.
