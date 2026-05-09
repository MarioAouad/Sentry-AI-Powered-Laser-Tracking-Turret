#ifndef CONFIG_H
#define CONFIG_H

// --- PIN DEFINITIONS ---
#define PIN_SERVO_PAN   12
#define PIN_SERVO_TILT  13
#define PIN_LASER       14
#define PIN_LED_GREEN   15  
#define PIN_LED_RED     2   

// --- SERIAL CONFIG ---
#define BAUD_RATE       115200 

// --- SERVO LIMITS ---
#define MIN_ANGLE       0
#define MAX_ANGLE       180
#define DEADBAND        1   

// --- SYSTEM STATES ---
enum SystemState {
    STATE_SCANNING = 0, // Green LED
    STATE_LOCKED   = 1, // Red LED + Laser [cite: 187]
    STATE_OFF      = 2  // All Off
};

#endif