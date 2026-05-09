#ifndef PAYLOAD_H
#define PAYLOAD_H

#include <Arduino.h>
#include "Config.h"

class Payload {
public:
    void init();
    void setScanningMode();
    void setLockedMode();
    void disableAll();
};

#endif