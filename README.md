# Sentry AI-Powered Laser Tracking Turret

## Objective
An active, autonomous "Eye-in-Hand" robotic sentry turret that actively tracks human subjects and dynamically targets specific body parts using a laser pointer. This project demonstrates the viability of combining modern deep learning (running on a local RTX 4060 GPU) with classical control theory on embedded edge hardware.

## Architecture Overview
This system utilizes a hybrid methodology to achieve real-time computational performance (>30 FPS). The workload is physically split into two nodes:
1. **Processing & Vision Hub (Python/PC):** Handles all heavy computer vision, pose estimation, multi-object tracking, and PID calculations.
2. **Actuation Hub (C++/ESP32-CAM):** Functions strictly as a network and control node. It streams video via Wi-Fi to the PC and executes PWM commands to move the turret and toggle the laser.

## Repository Structure
* `/python_vision/` - Contains the Python scripts, neural network models, and tracker logic.
* `/arduino_firmware/` - Contains the C++ firmware for the ESP32-CAM microcontroller.

## System Workflow
1. **Wake-Up Phase:** A low-power classical HOG+SVM cascade scans the ESP32 video stream for human gradients.
2. **Target Acquisition:** Upon detection, the YOLOv8-Pose model activates to extract skeletal keypoints.
3. **Tracking & Filtering:** ByteTrack/DeepSORT maintains target persistence, while an Exponential Moving Average (EMA) filter smooths the raw coordinate data.
4. **Kinematics:** A classical PID controller calculates the spatial error and generates dynamic servo angles.
5. **Actuation:** The PC transmits the required angles back to the ESP32-CAM to physically move the SG90 servos and illuminate the target with the 5V laser.