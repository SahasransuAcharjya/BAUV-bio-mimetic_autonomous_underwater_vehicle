#include <Servo.h>
#include <Wire.h>
#include <MPU6050.h>

Servo myservo;
MPU6050 mpu;

const int servoPin = 9;

float servoPos = 90.0;
float basePos = 90.0;
float amp = 0.0;
float freq = 0.0;
const float PI_VAL = 3.14159;

bool oscillating = false;
unsigned long oscillationStart = 0;
unsigned long lastServoUpdate = 0;
unsigned long lastMpuUpdate = 0;

void setup() {
  Serial.begin(115200);
  myservo.attach(servoPin);
  myservo.write((int)servoPos);

  Wire.begin();
  Wire.setClock(100000);

  Serial.println("SYS,BOOT");
  Serial.println("SYS,INIT_MPU");

  mpu.initialize();

  Wire.beginTransmission(0x68);
  Wire.write(0x6B);
  Wire.write(0x00);
  Wire.endTransmission(true);

  if (mpu.testConnection()) {
    Serial.println("SYS,MPU_OK");
  } else {
    Serial.println("SYS,MPU_FAIL");
  }

  Serial.println("SYS,READY");
}

void loop() {
  handleSerialCommands();
  updateServoOscillation();
  streamMPU();
}

void handleSerialCommands() {
  if (!Serial.available()) return;

  String cmd = Serial.readStringUntil('\n');
  cmd.trim();

  if (cmd.startsWith("CAL,")) {
    float angle = cmd.substring(4).toFloat();
    angle = constrain(angle, 0, 180);
    servoPos = angle;
    basePos = angle;
    oscillating = false;
    myservo.write((int)servoPos);
    Serial.print("SERVO,");
    Serial.println(servoPos, 2);
    Serial.println("STATUS,CAL_DONE");
  }

  else if (cmd.startsWith("OSC,")) {
    int firstComma = cmd.indexOf(',');
    int secondComma = cmd.indexOf(',', firstComma + 1);
    int thirdComma = cmd.indexOf(',', secondComma + 1);

    if (firstComma > 0 && secondComma > 0 && thirdComma > 0) {
      basePos = cmd.substring(firstComma + 1, secondComma).toFloat();
      freq = cmd.substring(secondComma + 1, thirdComma).toFloat();
      amp = cmd.substring(thirdComma + 1).toFloat();

      basePos = constrain(basePos, 0, 180);
      amp = max(0.0, amp);

      if ((basePos - amp) < 0) amp = basePos;
      if ((basePos + amp) > 180) amp = 180 - basePos;

      oscillating = true;
      oscillationStart = millis();

      Serial.print("STATUS,OSC_START,");
      Serial.print(basePos, 2);
      Serial.print(",");
      Serial.print(freq, 2);
      Serial.print(",");
      Serial.println(amp, 2);
    }
  }

  else if (cmd == "STOP") {
    oscillating = false;
    myservo.write((int)basePos);
    servoPos = basePos;
    Serial.print("SERVO,");
    Serial.println(servoPos, 2);
    Serial.println("STATUS,OSC_STOP");
  }
}

void updateServoOscillation() {
  if (!oscillating) return;

  unsigned long now = millis();
  if (now - lastServoUpdate < 20) return;  // ~50 Hz update
  lastServoUpdate = now;

  float t = (now - oscillationStart) / 1000.0;
  servoPos = basePos + amp * sin(2.0 * PI_VAL * freq * t);
  servoPos = constrain(servoPos, 0, 180);

  myservo.write((int)servoPos);

  Serial.print("SERVO,");
  Serial.println(servoPos, 2);
}

void streamMPU() {
  unsigned long now = millis();
  if (now - lastMpuUpdate < 100) return;   // 10 Hz stream
  lastMpuUpdate = now;

  int16_t ax, ay, az, gx, gy, gz;
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

  Serial.print("MPU,");
  Serial.print(ax); Serial.print(",");
  Serial.print(ay); Serial.print(",");
  Serial.print(az); Serial.print(",");
  Serial.print(gx); Serial.print(",");
  Serial.print(gy); Serial.print(",");
  Serial.println(gz);
  
  if (!oscillating) {
    Serial.print("SERVO,");
    Serial.println(servoPos, 2);
  }
}