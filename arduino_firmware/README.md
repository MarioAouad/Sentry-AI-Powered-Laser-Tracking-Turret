# Sentry Turret: Edge Node Firmware

## Overview
[cite_start]This module represents the "Muscle" of the active sentry turret[cite: 3, 34]. It contains the C++ firmware for the ESP32 microcontroller. [cite_start]To achieve true zero-latency tracking, this architecture strictly divides computational heavy lifting from physical actuation[cite: 6, 34]. 

[cite_start]The ESP32 acts purely as a low-latency edge motor controller[cite: 12]. [cite_start]It possesses no onboard intelligence and does not process video[cite: 12, 13, 34]. [cite_start]Instead, it waits for predictive inverse kinematic coordinates calculated by the local RTX 4060 compute node and instantly translates them into physical servo movements via a high-speed serial tether[cite: 8, 10, 84, 87, 88].

## Embedded Components
* [cite_start]**Processing:** ESP32 / ESP32-CAM (repurposed strictly as a logic controller)[cite: 12].
* [cite_start]**Actuation (2-DOF):** 2x SG90 Micro Servos configured in a pan-tilt linkage for X-axis (yaw) and Y-axis (pitch) targeting[cite: 18, 19].
* [cite_start]**Payload:** 5V Laser Diode, mounted mechanically parallel to the primary vision sensor to eliminate parallax error[cite: 22, 23].
* [cite_start]**Status Indicators:** 2x 5V LEDs (Red/Green) indicating the system's operational state (Scanning vs. Target Locked)[cite: 25].
* [cite_start]**Power Delivery:** Dedicated, hardwired 5V DC power supply routed through a distribution board to separate high-current servo draw from logic-level signals, preventing microcontroller brownouts[cite: 28, 29].

## Firmware Architecture & File Structure
The codebase is heavily modularized to separate communication, actuation, and payload logic from the main operational loop.

* `TurretNode.ino` **(The Orchestrator):** The main setup and execution loop. It is intentionally lightweight, acting only as the manager that passes coordinate data from the Serial Parser to the Servo Controller.
* `Config.h` **(System Settings):** The master configuration file. Contains all GPIO pin definitions, serial baud rates, mathematical constraints (min/max angles), and the deadband threshold to prevent micro-stuttering in the SG90 gears.
* `SerialParser.h` & `.cpp` **(The Data Tether):** Handles the high-speed, zero-latency UART communication with the Python compute node. It reads incoming comma-separated strings (e.g., `120,45,1\n`), extracts the absolute Pan angle, Tilt angle, and System State, and feeds them to the main loop.
* `ServoControl.h` & `.cpp` **(Kinematics Execution):** Utilizes the `ESP32Servo` library to allocate hardware timers. It translates the mathematical angles into stable PWM signals, enforces physical hardware limits to protect the gears, and applies deadband filtering for smooth tracking.
* `Payload.h` & `.cpp` **(Visual Feedback):** Manages the logic states for the visual indicators, turning the targeting laser and corresponding status LEDs on or off depending on whether the system is actively tracking a subject or scanning an empty room.

## Installation & Flashing
1. Open `TurretNode.ino` in the Arduino IDE.
2. Navigate to **Tools > Manage Libraries** and install the **`ESP32Servo`** library by Kevin Harrington.
3. Ensure you have the **esp32 by Espressif Systems** package installed via the Boards Manager.
4. Select your specific ESP32 board (e.g., **AI Thinker ESP32-CAM**) from the Boards menu.
5. Review `Config.h` to ensure the defined GPIO pins match your physical wiring scheme.
6. [cite_start]Connect the ESP32 to your PC via an ESP32-CAM-MB Shield or FTDI Programmer (ensure GPIO 0 is grounded during flashing if using a raw FTDI module)[cite: 14, 15].
7. Compile and Upload.
8. Once successfully flashed, remove the programming jumper and connect the primary USB-to-TTL data tether to the compute node.