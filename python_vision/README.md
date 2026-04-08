# Deep Learning Pipeline (Vision & Tracking)

## Overview
This module represents the "Brain" of the sentry turret. Running locally on a NVIDIA GPU, this Python-based pipeline captures the live VGA stream from the ESP32-CAM, processes the frames to locate targets, and transmits spatial correction angles back to the microcontroller.

## Core Modules
* **Classical Pre-processing (Level 1):** A Histogram of Oriented Gradients (HOG) paired with a Support Vector Machine (SVM) acts as a computationally lightweight "Wake-Up" cascade. It prevents the system from running heavy deep learning inference on an empty room.
* **Pose Estimation (Level 2):** YOLOv8-Pose (or MediaPipe Blaze Pose) extracts specific skeletal joints (head, chest, hand) for targeted locking.
* **Multi-Object Tracking (MOT):** ByteTrack / DeepSORT is implemented to prevent frame-to-frame amnesia and maintain target persistence through environmental occlusions.
* **Signal Filtering:** An Exponential Moving Average (EMA) low-pass filter mathematically smooths the raw pixel coordinates to prevent turret jitter.
* **Kinematics Engine:** A Proportional-Integral-Derivative (PID) controller converts the spatial pixel error (the delta between the smoothed AI keypoint and the absolute center of the frame) into mechanical servo angles to prevent violent snapping or overshooting.

## Setup & Execution
1. Create a virtual environment (Anaconda recommended).
2. Install the required dependencies: `pip install -r requirements.txt`
3. Ensure the ESP32-CAM is powered on and streaming to your local network.
4. Update the IP address in `main_tracker.py` to match your ESP32-CAM's IP.
5. Run the tracker: `python main_tracker.py`