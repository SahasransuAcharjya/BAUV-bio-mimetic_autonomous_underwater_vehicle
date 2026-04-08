#include <TinyGPS++.h>

// The UNO R4 Minima uses Serial1 for hardware pins 0 and 1
// We do NOT need SoftwareSerial for this board.
#define gpsSerial Serial1

TinyGPSPlus gps;

void setup() {
  // Start communication with the PC (Serial Monitor)
  Serial.begin(9600);
  
  // Start communication with the Neo-7M GPS
  gpsSerial.begin(9600); 

  Serial.println("--- GPS Coordinate Tracker ---");
  Serial.println("Waiting for satellite lock...");
  Serial.println("Note: Ensure the antenna is outdoors or by a window.");
}

void loop() {
  // Read data from the GPS module
  while (gpsSerial.available() > 0) {
    if (gps.encode(gpsSerial.read())) {
      displayCoordinates();
    }
  }

  // If no data is received for 5 seconds, warn the user
  if (millis() > 5000 && gps.charsProcessed() < 10) {
    Serial.println("Check Wiring: No data received from GPS.");
    delay(2000);
  }
}

void displayCoordinates() {
  if (gps.location.isValid()) {
    Serial.print("Latitude:  ");
    Serial.println(gps.location.lat(), 6); // 6 decimal places for precision
    
    Serial.print("Longitude: ");
    Serial.println(gps.location.lng(), 6);
    
    Serial.print("Altitude:  ");
    Serial.print(gps.altitude.meters());
    Serial.println("m");

    Serial.print("Satellites in view: ");
    Serial.println(gps.satellites.value());
    
    Serial.println("---------------------------");
  } else {
    // If the module is talking but hasn't locked onto satellites yet
    Serial.print("Searching... Satellites detected: ");
    Serial.println(gps.satellites.value());
  }
}