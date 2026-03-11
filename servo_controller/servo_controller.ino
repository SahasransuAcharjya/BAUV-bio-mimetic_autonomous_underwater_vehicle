#include <Servo.h>

Servo myservo;
float pos = 0;
int pin = 9;
float time = 0, timei = 0;
float pi = 3.14159, amp = 0, freq = 0, base_angle = 0, thres = 0;

void setup() {
  Serial.begin(9600);
  myservo.attach(pin);
  Serial.println("BAUV Servo Ready");  // Dashboard sees this
  delay(1000);
}

void loop() {
  if (Serial.available() > 0) {
    float command = Serial.parseFloat();
    while (Serial.available() > 0) Serial.read();  // Clear buffer
    
    if (command == 1) {
      calibrate();
    } else if (command == 2) {
      oscillate();
    }
  }
}

void calibrate() {
  Serial.println("Calibrate mode");
  while (Serial.available() == 0) delay(10);
  float angle = Serial.parseFloat();
  angle = constrain(angle, 0, 180);
  myservo.write(angle);
  
  // FEEDBACK FOR DASHBOARD
  Serial.print("pos:"); 
  Serial.println(angle, 1);
  Serial.println("Calibrated OK");
}

void oscillate() {
  Serial.println("Oscillate mode");
  
  // Get base angle
  while (Serial.available() == 0) delay(10);
  base_angle = Serial.parseFloat();
  base_angle = constrain(base_angle, 0, 180);
  
  // Get frequency
  while (Serial.available() == 0) delay(10);
  freq = Serial.parseFloat();
  freq = constrain(freq, 0.1, 5.0);
  
  // Get amplitude
  while (Serial.available() == 0) delay(10);
  amp = Serial.parseFloat();
  amp = constrain(amp, 5, 60);
  
  Serial.print("Starting: base="); Serial.print(base_angle);
  Serial.print(" freq="); Serial.print(freq);
  Serial.print(" amp="); Serial.println(amp);
  
  time = millis() / 100.0;
  thres = 60.0 / freq;  // 10 cycles
  
  while ((millis() / 100.0 - time) < thres) {
    timei = millis() / 100.0;
    pos = base_angle + amp * sin(2 * pi * freq * (timei - time));
    pos = constrain(pos, 0, 180);
    
    myservo.write((int)pos);
    
    // LIVE FEEDBACK - This makes graph move!
    Serial.print("pos:"); 
    Serial.println(pos, 1);
    
    delay(15);  // 66Hz smooth animation
  }
  Serial.println("Flapping complete");
}
