#ifndef SERVOCONTROL_H
#define SERVOCONTROL_H

#include <ESP32Servo.h>
#include "Config.h"

class ServoControl {
private:
    Servo panServo;
    Servo tiltServo;
    int currentPan = 90;
    int currentTilt = 90;

public:
    void init();
    void moveTo(int targetPan, int targetTilt);
};

#endif