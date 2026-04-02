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
      case 3: stop_flapping(); break; // NEW: Stop command
      default: Serial.println("unknown"); break;
    }
  }
  
  // Continuous oscillation if active
  if (oscillating) {
    run_oscillation();
  }
}

void calibrate() {
  Serial.println("cal:wait");
  while (Serial.available() == 0) delay(10);
  
  float value = Serial.parseFloat();
  if (!isnan(value) && value >= 0 && value <= 180) {
    myservo.write(value);
    pos = value;
    Serial.print("pos:");
    Serial.println(pos, 2);
    Serial.println("cal:done");
  }
}

void oscillate() {
  float base_pos;
  
  // Get base position
  Serial.println("osc:base");
  while (Serial.available() == 0) delay(10);
  base_pos = Serial.parseFloat();
  if (!isnan(base_pos) && base_pos >= 0 && base_pos <= 180) {
    Serial.print("base:"); Serial.println(base_pos, 2);
  }
  
  // Get frequency
  Serial.println("osc:freq");
  while (Serial.available() == 0) delay(10);
  freq = Serial.parseFloat();
  if (!isnan(freq) && freq > 0 && freq <= 5) {
    Serial.print("freq:"); Serial.println(freq, 2);
  }
  
  // Get amplitude
  Serial.println("osc:amp");
  while (Serial.available() == 0) delay(10);
  amp = Serial.parseFloat();
  if (!isnan(amp) && amp >= 5 && (base_pos - amp >= 0) && (base_pos + amp <= 180)) {
    Serial.print("amp:");
    Serial.println(amp, 2);
    Serial.println("osc:start");
    
    oscillating = true;
    time_start = millis();
  }
}

void run_oscillation() {
  unsigned long current_time = millis();
  float t = (current_time - time_start) / 1000.0;  // Time in seconds
  
  pos = 90 + amp * sin(2 * pi * freq * t);
  // Correct sine wave
  pos = constrain(pos, 0, 180);
  myservo.write(pos);
  
  Serial.print("pos:"); Serial.println(pos, 2);
  
  // Note: The 10-second timeout constraint was removed so it flaps continuously
  delay(20);  // 50Hz update rate
}

// NEW: Function to stop the servo
void stop_flapping() {
  oscillating = false;
  Serial.println("osc:stopped");
}