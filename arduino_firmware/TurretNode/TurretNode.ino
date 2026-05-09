#include "Config.h"
#include "SerialParser.h"
#include "ServoControl.h"
#include "Payload.h"

SerialParser comms;
ServoControl turret;
Payload payload;

int targetPan = 90;
int targetTilt = 90;
int systemState = STATE_SCANNING;

void setup() {
    comms.init();    // Starts Serial at 115200 [cite: 184]
    payload.init();  // Sets Pins to OUTPUT [cite: 184]
    turret.init();   // Attaches Servos [cite: 184]
    payload.setScanningMode(); // Default Green [cite: 185]
}

void loop() {
    // Check for incoming data: PAN,TILT,STATE [cite: 186]
    if (comms.checkForCommands(targetPan, targetTilt, systemState)) {
        
        // Move motors regardless of LED state
        turret.moveTo(targetPan, targetTilt);
        
        // Handle Payload States
        switch(systemState) {
            case STATE_LOCKED:
                payload.setLockedMode(); // Red + Laser [cite: 187]
                break;
            case STATE_OFF:
                payload.disableAll();    // Everything Off
                break;
            case STATE_SCANNING:
            default:
                payload.setScanningMode(); // Green [cite: 188]
                break;
        }
    }
}