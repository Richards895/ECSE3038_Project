#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h>  
#include "env.h"


#define LED_PIN 22       
#define FAN_PIN 23       
#define MOTION_PIN 15   
#define ONE_WIRE_PIN 4   

OneWire oneWire(ONE_WIRE_PIN);
DallasTemperature sensors(&oneWire);
 
void setup(){
   
  pinMode(LED_PIN, OUTPUT);
  pinMode(FAN_PIN, OUTPUT);
  pinMode(MOTION_PIN, INPUT);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(FAN_PIN, LOW);

Serial.begin(115200); 
sensors.begin(); 

 WiFi.begin( SSID,PASS );
   
 while (WiFi.status() != WL_CONNECTED){
    delay(500);
    Serial.print(".");   
 }

 Serial.print("Connected to the Wifi Network with IP addess: ");
 Serial.println(WiFi.localIP());

  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
}

float readTemperature() {
  sensors.requestTemperatures();
  for (int i = 0; i < 2; i++) {
    float tempC = sensors.getTempCByIndex(0);
    if (tempC != DEVICE_DISCONNECTED_C) {
      Serial.printf("Temperature: %.2f°C\n", tempC);
      return tempC;
    }
    delay(100); 
  }
  Serial.println("DS18B20 not detected!");
  return -999;
}

String getCurrentTimeString() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    Serial.println("Failed to get time");
    return "00:00:00";
  }
  char timeStr[9];
  sprintf(timeStr, "%02d:%02d:%02d", timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
  return String(timeStr);
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    float temperature = readTemperature();
    if (temperature == -999) return;

    int motion = digitalRead(MOTION_PIN);
    String currentTime = getCurrentTimeString();

    String url = String(ENDPOINT) + "?temp=" + temperature + "&motion=" + motion + "&current_time=" + currentTime;
    Serial.println("Sending request to: " + url);

    HTTPClient http;
    http.begin(url);
    int responseCode = http.GET();

    if (responseCode > 0) {
      String response = http.getString();
      Serial.println("Response: " + response);

      JsonDocument doc;
      DeserializationError error = deserializeJson(doc, response);
      if (!error) {
        bool fan = doc["fan"];
        bool light = doc["light"];
        digitalWrite(FAN_PIN, fan ? HIGH : LOW);
        digitalWrite(LED_PIN, light ? HIGH : LOW);
        Serial.printf("Fan: %s | Light: %s\n", fan ? "ON" : "OFF", light ? "ON" : "OFF");
      } else {
        Serial.println("JSON parse error: " + String(error.c_str()));
      }
    } else {
      Serial.printf("GET failed: %s\n", http.errorToString(responseCode).c_str());
    }

    http.end();
  }

  delay(10000);  
}

