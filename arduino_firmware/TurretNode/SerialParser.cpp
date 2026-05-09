#include "SerialParser.h"
#include "Config.h"

void SerialParser::init() {
    Serial.begin(BAUD_RATE);
    // Clear buffer on startup
    while (Serial.available()) {
        Serial.read();
    }
}

// Returns true if a valid new command was parsed
bool SerialParser::checkForCommands(int &outPan, int &outTilt, int &outState) {
    if (Serial.available() > 0) {
        // Read until newline character
        String incomingData = Serial.readStringUntil('\n');
        
        // Expected format: PAN,TILT,STATE (e.g. "90,90,0")
        int firstComma = incomingData.indexOf(',');
        int secondComma = incomingData.indexOf(',', firstComma + 1);
        
        if (firstComma > 0 && secondComma > firstComma) {
            outPan = incomingData.substring(0, firstComma).toInt();
            outTilt = incomingData.substring(firstComma + 1, secondComma).toInt();
            outState = incomingData.substring(secondComma + 1).toInt();
            return true;
        }
    }
    return false;
}