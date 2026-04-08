# Hardware Control & Microcontroller Firmware

## Overview
This module represents the "Muscle and Eyes" of the sentry turret. It contains the C++ firmware for the ESP32-CAM. The microcontroller acts purely as a physical translation layer—it has no onboard intelligence. It streams raw video out, and accepts processed kinematic commands in.

## Embedded Components
* **Processing:** ESP32-CAM (with OV2640 Sensor).
* **Actuation (2-DOF):** 2x SG90 Micro Servos configured in a pan-tilt linkage for X-axis (yaw) and Y-axis (pitch) movements.
* **Payload:** 5V Laser Diode mounted parallel to the camera lens to eliminate parallax error.
* **Status Indicators:** 2x 5V LEDs (Red/Green) indicating the system state (Scanning vs. Locked).
* **Power Delivery:** Dedicated, hardwired 5V DC Adapter to prevent microcontroller brownouts during peak servo current draw.

## Code Structure
* `TurretNode.ino`: The main setup and loop functions.
* `wifi_setup.h`: Handles the local network connection and the HTTP video streaming server.
* `servo_kinematics.h`: Listens for incoming angle data from the Python script and outputs the appropriate PWM signals to the GPIO pins connected to the SG90s.

## Installation & Flashing
1. Open `TurretNode.ino` in the Arduino IDE.
2. Ensure you have the **esp32 by Espressif Systems** package installed via the Boards Manager.
3. Select **AI Thinker ESP32-CAM** from the Boards menu.
4. Update your Wi-Fi SSID and Password in the configuration file.
5. Connect the ESP32-CAM to your PC via an ESP32-CAM-MB Shield or FTDI Programmer (ensure GPIO 0 is grounded during flashing if using FTDI).
6. Compile and Upload.