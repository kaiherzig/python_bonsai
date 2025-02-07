import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import json
import time
from datetime import datetime
import threading

# ==== KONFIGURATION ====
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "miflora/Bonsai"
FEUCHTIGKEIT_GRENZE = 50  # Prozentwert für Feuchtigkeitsschwelle
RELAIS_GPIO = 21  # GPIO-Pin für das Relais (Pumpe)
RELAIS2_GPIO = 26
PUMPEN_LAUFZEIT = 1  # Dauer in Sekunden
ALARM_TIMEOUT = 10800  # 3 Stunden = 10800 Sekunden

# ==== SETUP GPIO ====
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAIS_GPIO, GPIO.OUT)
GPIO.setup(RELAIS2_GPIO, GPIO.OUT)
GPIO.output(RELAIS_GPIO, GPIO.HIGH)  # Relais startet ausgeschaltet (LOW-Trigger-Logik)
GPIO.output(RELAIS2_GPIO, GPIO.HIGH)

# Letzte bekannte Feuchtigkeit speichern
letzte_feuchtigkeit = None
letzte_messung = time.time()  # Zeitpunkt der letzten Messung wird gesetzt

# ==== HILFSFUNKTION FÜR ZEITSTEMPEL ====
def log(message):
    """ Debugging-Log mit Zeitstempel """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

# ==== CALLBACK FUNKTION (wird bei MQTT-Nachricht aufgerufen) ====
def on_message(client, userdata, message):
    global letzte_feuchtigkeit, letzte_messung  # Globale Variablen für letzte Messwerte

    log(f"📩 MQTT-Nachricht empfangen von {message.topic}")
    payload = message.payload.decode("utf-8")
    log(f"📜 Rohdaten: {payload}")

    try:
        data = json.loads(payload)  # JSON-Daten parsen
        log("✅ JSON erfolgreich geparst!")

        if "moisture" in data:
            feuchtigkeit = data["moisture"]
            letzte_feuchtigkeit = feuchtigkeit
            letzte_messung = time.time()  # Zeitpunkt der letzten Messung speichern
            log(f"🌱 Bonsai Feuchtigkeit: {feuchtigkeit}% (Schwelle: {FEUCHTIGKEIT_GRENZE}%)")

            if feuchtigkeit < FEUCHTIGKEIT_GRENZE:
                log("🚰 Feuchtigkeit zu niedrig! Pumpe wird eingeschaltet.")
                GPIO.output(RELAIS_GPIO, GPIO.LOW)  # Pumpe AN (LOW-Trigger)
                time.sleep(PUMPEN_LAUFZEIT)
                GPIO.output(RELAIS_GPIO, GPIO.HIGH)  # Pumpe AUS (LOW-Trigger)
                log("✅ Pumpe gestoppt.")
            else:
                log("✅ Feuchtigkeit ist ausreichend. Keine Aktion nötig.")

        else:
            log("⚠️ Warnung: Kein Feuchtigkeitswert in den Daten gefunden!")

    except json.JSONDecodeError:
        log("❌ Fehler: JSON konnte nicht geparst werden!")

    # Nach Abschluss einer Aktion immer wieder warten auf neue Feuchtigkeitswerte
    log(f"📡 Warte auf Feuchtigkeitswerte von {MQTT_TOPIC} ...")

# ==== FUNKTION ZUR PRÜFUNG DES ALARM-TIMEOUTS ====
def check_mqtt_timeout():
    while True:
        time.sleep(60)  # Jede Minute prüfen
        zeit_seit_letzter_messung = time.time() - letzte_messung
        if zeit_seit_letzter_messung > ALARM_TIMEOUT:
            log("🚨 ALARM: Seit mehr als 3 Stunden keine neuen Sensordaten empfangen!")

# ==== MQTT-CLIENT INITIALISIEREN ====
client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT)

# Abonnieren des Bonsai-Themas
client.subscribe(MQTT_TOPIC)
log(f"📡 Warte auf Feuchtigkeitswerte von {MQTT_TOPIC} ...")

# ==== THREAD FÜR ALARMÜBERWACHUNG ====
timeout_thread = threading.Thread(target=check_mqtt_timeout, daemon=True)
timeout_thread.start()

# Endlosschleife zum Warten auf MQTT-Nachrichten
try:
    client.loop_forever()
except KeyboardInterrupt:
    log("❌ Programm manuell beendet.")
    GPIO.cleanup()
    log("✅ GPIO-Pins freigegeben. Relais zurückgesetzt.")