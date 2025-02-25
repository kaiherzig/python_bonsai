import ssl
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import json
import time
from datetime import datetime
import threading

# ==== KONFIGURATION ====
MQTT_BROKER = "<<mqtt>>"
MQTT_PORT = 8883
MQTT_TOPIC = "miflora/Bonsai"
MQTT_PUMP_TOPIC = "pump/status"  # MQTT-Topic für Pumpenstatus

FEUCHTIGKEIT_GRENZE = 40  # Prozentwert für Feuchtigkeitsschwelle
RELAIS_GPIO = 21  # GPIO-Pin für das Relais (Pumpe)
RELAIS2_GPIO = 26
PUMPEN_LAUFZEIT = 1  # **Pumpe läuft genau 1 Sekunde**
ALARM_TIMEOUT = 10800  # 3 Stunden = 10800 Sekunden

# ==== TLS-ZERTIFIKATE ====
CA_CERT = "<<path-to-mosquitto-ca.crt>>"
CLIENT_CERT = "<<path-to-mosquitto-client.crt>>"
CLIENT_KEY = "<<path-to-mosquitto-client.key>>"

# ==== SETUP GPIO ====
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAIS_GPIO, GPIO.OUT)
GPIO.setup(RELAIS2_GPIO, GPIO.OUT)
GPIO.output(RELAIS_GPIO, GPIO.HIGH)  # Relais startet ausgeschaltet
GPIO.output(RELAIS2_GPIO, GPIO.HIGH)

# MQTT-Client initialisieren
client = mqtt.Client()

# TLS aktivieren
client.tls_set(
    ca_certs=CA_CERT,
    certfile=CLIENT_CERT,
    keyfile=CLIENT_KEY,
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)

# Verbindung zum MQTT-Broker herstellen (mit Fehlerbehandlung)
try:
    client.connect(MQTT_BROKER, MQTT_PORT)
    print("✅ Verbindung zum MQTT-Broker über TLS erfolgreich!")
except Exception as e:
    print(f"❌ Fehler: {e}")

# Letzte bekannte Feuchtigkeit speichern
letzte_feuchtigkeit = None
letzte_messung = time.time()

# ==== CALLBACK FUNKTION (bei MQTT-Nachricht) ====
def on_message(client, userdata, message):
    global letzte_feuchtigkeit, letzte_messung

    print(f"📩 MQTT-Nachricht empfangen von {message.topic}")
    payload = message.payload.decode("utf-8")
    print(f"📜 Rohdaten: {payload}")

    try:
        data = json.loads(payload)
        print("✅ JSON erfolgreich geparst!")

        if "moisture" in data:
            feuchtigkeit = data["moisture"]
            letzte_feuchtigkeit = feuchtigkeit
            letzte_messung = time.time()
            print(f"🌱 Bonsai Feuchtigkeit: {feuchtigkeit}% (Schwelle: {FEUCHTIGKEIT_GRENZE}%)")

            if feuchtigkeit < FEUCHTIGKEIT_GRENZE:
                print("🚰 Feuchtigkeit zu niedrig! Pumpe wird eingeschaltet.")
                client.publish(MQTT_PUMP_TOPIC, json.dumps({"status": "ON", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}))
                
                GPIO.output(RELAIS_GPIO, GPIO.LOW)  # Pumpe AN
                time.sleep(PUMPEN_LAUFZEIT)  # **1 Sekunde Pumpenlaufzeit**
                GPIO.output(RELAIS_GPIO, GPIO.HIGH)  # Pumpe AUS
                
                client.publish(MQTT_PUMP_TOPIC, json.dumps({"status": "OFF", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}))
                print("✅ Pumpe gestoppt.")
            else:
                print("✅ Feuchtigkeit ist ausreichend. Keine Aktion nötig.")

        else:
            print("⚠️ Kein Feuchtigkeitswert gefunden!")

    except json.JSONDecodeError:
        print("❌ Fehler: JSON konnte nicht geparst werden!")

    print(f"📡 Warte auf Feuchtigkeitswerte von {MQTT_TOPIC} ...")

# ==== FUNKTION ZUR PRÜFUNG DES ALARM-TIMEOUTS ====
def check_mqtt_timeout():
    while True:
        time.sleep(60)  
        zeit_seit_letzter_messung = time.time() - letzte_messung
        if zeit_seit_letzter_messung > ALARM_TIMEOUT:
            print("🚨 ALARM: Seit mehr als 3 Stunden keine neuen Sensordaten empfangen!")

# ==== MQTT RECONNECT FUNKTION ====
def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("⚠️ Verbindung zum MQTT-Broker unterbrochen! Versuche erneut zu verbinden...")
        while True:
            try:
                client.reconnect()
                print("✅ MQTT Reconnect erfolgreich!")
                break
            except Exception as e:
                print(f"❌ Reconnect fehlgeschlagen: {e}")
                time.sleep(5)

# Callbacks setzen und Abonnement starten
client.on_message = on_message
client.on_disconnect = on_disconnect  # Automatischer Reconnect
client.subscribe(MQTT_TOPIC)

# Starte Überwachungs-Thread für MQTT-Timeouts
timeout_thread = threading.Thread(target=check_mqtt_timeout, daemon=True)
timeout_thread.start()

try:
    client.loop_forever()
except KeyboardInterrupt:
    print("\n🔴 Programm wird beendet. GPIOs werden freigegeben.")
finally:
    GPIO.cleanup()
    print("✅ GPIO-Pins freigegeben. Relais zurückgesetzt.")