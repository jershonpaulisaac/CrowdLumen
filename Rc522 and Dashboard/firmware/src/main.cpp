#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// --- CONFIGURATION ---
const char* WIFI_SSID = "JERSHON-LAP 7737";
const char* WIFI_PASS = "christ$$777";
const char* BASE_URL = "http://192.168.137.1:5000/api"; 

// --- PIN MAPPING ---
#define SS_PIN_1  21   // Reader 1 (Entry)
#define SS_PIN_2  5    // Reader 2 (Exit)
#define RST_PIN   22   // Shared Reset
#define BUZZER    15
#define LED_SYS_G 16
#define LED_SYS_R 17
#define LED_ACT_G 4
#define LED_ACT_R 2

// --- OBJECTS ---
MFRC522 reader1(SS_PIN_1, RST_PIN);
MFRC522 reader2(SS_PIN_2, RST_PIN);

// --- STATE ---
bool alarmActive = false;
bool overCapAlarm = false;
unsigned long lastEvacCheck = 0;

// --- UTILS ---
void beep(int times, int duration) {
  for(int i=0; i<times; i++) {
    digitalWrite(BUZZER, HIGH);
    delay(duration);
    digitalWrite(BUZZER, LOW);
    if(times > 1) delay(50);
  }
}

void feedbackSuccess() {
  digitalWrite(LED_ACT_G, HIGH);
  beep(1, 100);
  delay(1000);
  digitalWrite(LED_ACT_G, LOW);
}

void feedbackDeny() {
  digitalWrite(LED_ACT_R, HIGH);
  beep(2, 100);
  delay(1000);
  digitalWrite(LED_ACT_R, LOW);
}

void checkHardwareStatus() {
  if (WiFi.status() == WL_CONNECTED && (millis() - lastEvacCheck > 2000)) {
    lastEvacCheck = millis();
    HTTPClient http;
    http.begin(String(BASE_URL) + "/hw_status");
    int code = http.GET();
    if (code == 200) {
      String payload = http.getString();
      DynamicJsonDocument doc(512);
      deserializeJson(doc, payload);
      alarmActive = doc["evac"];
      overCapAlarm = doc["over_cap"];
    }
    http.end();
  }
}

void sendTap(String uid, String type) {
  if(WiFi.status() == WL_CONNECTED){
    HTTPClient http;
    http.begin(String(BASE_URL) + "/tap");
    http.addHeader("Content-Type", "application/json");
    String json = "{\"uid\": \"" + uid + "\", \"type\": \"" + type + "\"}";
    int code = http.POST(json);
    if(code == 200) {
       String payload = http.getString();
       DynamicJsonDocument doc(512);
       deserializeJson(doc, payload);
       if(strcmp(doc["status"], "allowed") == 0) feedbackSuccess();
       else feedbackDeny();
    } else {
       feedbackDeny();
    }
    http.end();
  } else feedbackDeny();
}

String readUID(MFRC522 &mfrc522) {
  String content= "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
     content.concat(String(mfrc522.uid.uidByte[i] < 0x10 ? "0" : ""));
     content.concat(String(mfrc522.uid.uidByte[i], HEX));
  }
  content.toUpperCase();
  return content;
}

void setup() {
  Serial.begin(115200);
  pinMode(BUZZER, OUTPUT);
  pinMode(LED_SYS_G, OUTPUT);
  pinMode(LED_SYS_R, OUTPUT);
  pinMode(LED_ACT_G, OUTPUT);
  pinMode(LED_ACT_R, OUTPUT);

  SPI.begin();
  reader1.PCD_Init();
  reader2.PCD_Init();
  
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    digitalWrite(LED_SYS_R, !digitalRead(LED_SYS_R));
  }
  digitalWrite(LED_SYS_R, LOW);
  digitalWrite(LED_SYS_G, HIGH);
  beep(2, 100);
}

void loop() {
  checkHardwareStatus();

  if (alarmActive) {
    digitalWrite(BUZZER, HIGH);
    digitalWrite(LED_SYS_R, HIGH);
    delay(200);
    digitalWrite(BUZZER, LOW);
    digitalWrite(LED_SYS_R, LOW);
    delay(200);
    return;
  }

  if (overCapAlarm) {
    digitalWrite(BUZZER, HIGH);
    digitalWrite(LED_ACT_R, HIGH);
    delay(100);
    digitalWrite(BUZZER, LOW);
    digitalWrite(LED_ACT_R, LOW);
    delay(1000); 
  }

  if (reader1.PICC_IsNewCardPresent() && reader1.PICC_ReadCardSerial()) {
     sendTap(readUID(reader1), "entry");
     reader1.PICC_HaltA();
     reader1.PCD_StopCrypto1();
  }

  if (reader2.PICC_IsNewCardPresent() && reader2.PICC_ReadCardSerial()) {
     sendTap(readUID(reader2), "exit");
     reader2.PICC_HaltA();
     reader2.PCD_StopCrypto1();
  }
}
