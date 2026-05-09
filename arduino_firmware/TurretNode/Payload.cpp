#include "Payload.h"

void Payload::init() {
    pinMode(PIN_LASER, OUTPUT);
    pinMode(PIN_LED_GREEN, OUTPUT);
    pinMode(PIN_LED_RED, OUTPUT);
    disableAll();
}

void Payload::setScanningMode() {
    digitalWrite(PIN_LASER, LOW);       // Laser OFF while scanning
    digitalWrite(PIN_LED_GREEN, HIGH);  // Green LED ON
    digitalWrite(PIN_LED_RED, LOW);     // Red LED OFF
}

void Payload::setLockedMode() {
    digitalWrite(PIN_LASER, HIGH);      // Laser ON to indicate lock
    digitalWrite(PIN_LED_GREEN, LOW);   // Green LED OFF
    digitalWrite(PIN_LED_RED, HIGH);    // Red LED ON
}

void Payload::disableAll() {
    digitalWrite(PIN_LASER, LOW);
    digitalWrite(PIN_LED_GREEN, LOW);
    digitalWrite(PIN_LED_RED, LOW);
}