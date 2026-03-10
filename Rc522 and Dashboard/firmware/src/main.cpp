#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <vector>
#include <map>

// --- CONFIGURATION ---
const char* WIFI_SSID = "JERSHON-LAP 7737";
const char* WIFI_PASS = "christ$$777";
const char* BASE_URL = "http://192.168.137.1:5001/api"; 

// --- PIN MAPPING (NEW) ---
#define LED_GREEN 2
#define LED_RED   5
#define BUZZER    4

// --- STATE ---
bool alarmActive = false;
bool overCapAlarm = false;
unsigned long lastEvacCheck = 0;

// --- BLE MULTI-TRACKING STATE ---
int scanTime = 2; // scan interval in seconds
BLEScan* pBLEScan;
struct PhoneState {
  unsigned long lastSeen;
  bool isInVenue;
};
std::map<String, PhoneState> activeDevices;
std::vector<String> pendingEntries;
std::vector<String> pendingExits;
portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;

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
  digitalWrite(LED_GREEN, HIGH);
  beep(1, 100);  // 1 beep for allowed entry
  delay(100);
  digitalWrite(LED_GREEN, LOW);
}

void feedbackAlreadyIn() {
  digitalWrite(LED_RED, HIGH);
  beep(2, 80);   // 2 beeps for denied / already in
  delay(40);
  digitalWrite(LED_RED, LOW);
}

void feedbackExit() {
  digitalWrite(LED_GREEN, HIGH);
  digitalWrite(LED_RED,   HIGH);
  beep(1, 60);   // 1 short beep for exit
  delay(140);
  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_RED,   LOW);
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
    // Forward the MAC address as UID and proper presence state ("entry" / "exit")
    String json = "{\"uid\": \"" + uid + "\", \"type\": \"" + type + "\"}";
    int code = http.POST(json);
    if(code == 200) {
       String payload = http.getString();
       DynamicJsonDocument doc(512);
       deserializeJson(doc, payload);
       
       if (type == "exit") {
         feedbackExit();
       } else if (type == "entry") {
         const char* msg = doc["msg"];
         if (msg && strstr(msg, "Already In")) {
           feedbackAlreadyIn();
         } else if (strcmp(doc["status"], "allowed") == 0) {
           feedbackSuccess();
         } else {
           feedbackAlreadyIn();
         }
       }
    } else {
       if (type == "entry") feedbackAlreadyIn();
    }
    http.end();
  } else {
    if (type == "entry") feedbackAlreadyIn();
  }
}

class MyAdvertisedDeviceCallbacks: public BLEAdvertisedDeviceCallbacks {
    void onResult(BLEAdvertisedDevice advertisedDevice) {
      // Proximity threshold: target devices that are in moderate close range (>-55 RSSI)
      // -35 was too strict because many phones have weaker Bluetooth broadcast power. 
      if (advertisedDevice.getRSSI() > -55) {
        String mac = advertisedDevice.getAddress().toString().c_str();
        mac.toUpperCase();
        mac.replace(":", ""); // Formatting MAC to look like standard UID 
        
        portENTER_CRITICAL(&mux);
        unsigned long currentMillis = millis();
        // Register new arrival if we haven't seen it, or it was outside the venue
        if (activeDevices.find(mac) == activeDevices.end() || !activeDevices[mac].isInVenue) {
          activeDevices[mac] = {currentMillis, true};
          pendingEntries.push_back(mac);
        } else {
          // Device still lingering in proximity, quietly update last tick
          activeDevices[mac].lastSeen = currentMillis;
        }
        portEXIT_CRITICAL(&mux);
      }
    }
};

void cleanupAndProcessTaps() {
  unsigned long currentMillis = millis();
  
  portENTER_CRITICAL(&mux);
  // Mark departures if device hasn't been seen for 20 seconds
  for (auto it = activeDevices.begin(); it != activeDevices.end(); ) {
    if (it->second.isInVenue && (currentMillis - it->second.lastSeen > 20000)) {
      pendingExits.push_back(it->first);
      it = activeDevices.erase(it);
    } else {
      ++it;
    }
  }
  
  // Clone queues for processing
  std::vector<String> entriesToProcess = pendingEntries;
  pendingEntries.clear();
  std::vector<String> exitsToProcess = pendingExits;
  pendingExits.clear();
  portEXIT_CRITICAL(&mux);

  // Output Network requests outside the critical section
  for(String mac : entriesToProcess) {
    sendTap(mac, "entry");
  }
  for(String mac : exitsToProcess) {
    sendTap(mac, "exit");
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(BUZZER, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_RED, OUTPUT);

  // WiFi Setup
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    digitalWrite(LED_RED, !digitalRead(LED_RED)); // Flashing RED on connection loop
  }
  digitalWrite(LED_RED, LOW);
  
  // Successful Boot Feedback
  digitalWrite(LED_GREEN, HIGH);
  beep(2, 100);
  delay(1000);
  digitalWrite(LED_GREEN, LOW);

  // BLE Setup
  BLEDevice::init("BLE_GateNode");
  pBLEScan = BLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setActiveScan(true); // Get more payload, takes a bit more power footprint
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);  
}

void loop() {
  checkHardwareStatus();

  // Priority Alarms
  if (alarmActive) {
    digitalWrite(BUZZER, HIGH);
    digitalWrite(LED_RED, HIGH);
    delay(200);
    digitalWrite(BUZZER, LOW);
    digitalWrite(LED_RED, LOW);
    delay(200);
    return;
  }

  if (overCapAlarm) {
    digitalWrite(BUZZER, HIGH);
    digitalWrite(LED_RED, HIGH);
    delay(100);
    digitalWrite(BUZZER, LOW);
    digitalWrite(LED_RED, LOW);
    delay(400); // 400ms to allow more frequent scanning cycles than a pure wait
  }

  // Scanning loop
  pBLEScan->start(scanTime, false);
  pBLEScan->clearResults(); 

  // Process REST pushes
  cleanupAndProcessTaps();
}
