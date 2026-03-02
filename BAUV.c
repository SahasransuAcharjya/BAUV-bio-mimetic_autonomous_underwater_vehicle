#include <Servo.h>

Servo myservo;  // create servo object to control a servo
// twelve servo objects can be created on most boards

float pos = 0;    // variable to store the servo position
int pin = 8;
float time = millis(), timei;
float pi = 3.1428, amp, freq, thres;

void setup() {
  Serial.begin(9600);
  myservo.attach(pin);  // attaches the servo on pin 9 to the servo object
}

void loop() {
  if(Serial.available())
    {
      int num = Serial.parseFloat();
      //Serial.println("Starting");
      switch (num)
        {
          case 1 :
            calibrate();
            break;
          case 2 :
            oscillate();
            break;
          default :
            //Serial.println("broke");
            break;
        }
    }
}

void calibrate()
{
  //Serial.println("Calibrating");
  while(1)
    {
      //Serial.println("Enter Value");
      //Serial.flush();
      if(Serial.available())
        {          
          int value = Serial.parseFloat();
          //Serial.println("hi");
          //Serial.println(value);          
          myservo.write(value);
          break;
        }
    }
}

void oscillate()
{
  while(1)
    {
      if(Serial.available())
        {
          float value = Serial.parseFloat();
          //myservo.write(value);
          
          while(1)
            {
              if(Serial.available())
                {
                  freq = Serial.parseFloat();                  
                  break;
                }
            }

          while(1)
            {
              if(Serial.available())
                {
                  amp = Serial.parseFloat();                  
                  break;
                }
            }
          
          time = millis()/1000.0;
          timei = millis()/1000.0;
          thres = 20.0/freq;
          while((timei-time)<thres)
            {
              timei = millis()/1000.0;
              pos = value + amp*sin(2*pi*freq*(timei-time));
              myservo.write(pos);
              //Serial.println(pos);
              //Serial.println(2*pi*freq*(timei-time));
              //Serial.println(millis());              
              delay(10);              
            }

          break;
        }
    }
}
