#include <Servo.h>

Servo myservo;
float pos = 0;
int pin = 9;
unsigned long time_start = 0;
float pi = 3.14159, amp = 0, freq = 0;
bool oscillating = false;

void setup() {
  Serial.begin(9600);
  myservo.attach(pin);
  Serial.println("Servo Dashboard Ready");
  delay(1000);
}

void loop() {
  if (Serial.available()) {
    float num = Serial.parseFloat();
    if (isnan(num)) return;
    
    switch ((int)num) {
      case 1: calibrate(); break;
      case 2: oscillate(); break;
      case 3: stop_flapping(); break;
      default: Serial.println("unknown"); break;
    }
  }
  
  if (oscillating) {
    run_oscillation();
  }
}

void calibrate() {
  while (Serial.available() == 0) delay(10);
  float value = Serial.parseFloat();
  if (!isnan(value) && value >= 0 && value <= 180) {
    myservo.write(value);
    pos = value;
    Serial.print("pos:"); Serial.println(pos, 2);
  }
}

void oscillate() {
  float base_pos;
  while (Serial.available() == 0) delay(10);
  base_pos = Serial.parseFloat();
  
  while (Serial.available() == 0) delay(10);
  freq = Serial.parseFloat();
  
  while (Serial.available() == 0) delay(10);
  amp = Serial.parseFloat();
  
  // UPDATED: Frequency limit increased to 10
  if (!isnan(freq) && freq > 0 && freq <= 10 && !isnan(amp)) {
    oscillating = true;
    time_start = millis();
    Serial.println("osc:start");
  }
}

void run_oscillation() {
  unsigned long current_time = millis();
  float t = (current_time - time_start) / 1000.0;
  pos = 90 + amp * sin(2 * pi * freq * t);
  pos = constrain(pos, 0, 180);
  myservo.write(pos);
  Serial.print("pos:"); Serial.println(pos, 2);
  delay(20); 
}

void stop_flapping() {
  oscillating = false;
  Serial.println("osc:stopped");
}