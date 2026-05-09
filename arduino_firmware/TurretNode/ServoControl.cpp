#include "ServoControl.h"

void ServoControl::init() {
    // Standard ESP32 timer allocation for servos
    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);
    
    panServo.setPeriodHertz(50);    // Standard 50Hz for SG90
    tiltServo.setPeriodHertz(50);
    
    panServo.attach(PIN_SERVO_PAN, 500, 2400);   // SG90 min/max pulse widths
    tiltServo.attach(PIN_SERVO_TILT, 500, 2400);

    // Center the turret on startup
    panServo.write(currentPan);
    tiltServo.write(currentTilt);
}

void ServoControl::moveTo(int targetPan, int targetTilt) {
    // 1. Constrain bounds to protect the plastic gears
    targetPan = constrain(targetPan, MIN_ANGLE, MAX_ANGLE);
    targetTilt = constrain(targetTilt, MIN_ANGLE, MAX_ANGLE);

    // 2. Apply Deadband to prevent jittering on minor mathematical fluctuations
    if (abs(targetPan - currentPan) >= DEADBAND) {
        panServo.write(targetPan);
        currentPan = targetPan;
    }
    
    if (abs(targetTilt - currentTilt) >= DEADBAND) {
        tiltServo.write(targetTilt);
        currentTilt = targetTilt;
    }
}