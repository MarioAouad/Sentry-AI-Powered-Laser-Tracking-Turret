#ifndef SERIALPARSER_H
#define SERIALPARSER_H

#include <Arduino.h>

class SerialParser {
public:
    void init();
    bool checkForCommands(int &outPan, int &outTilt, int &outState);
};

#endif