#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import psycopg2
import json
import requests
from datetime import datetime
import os

# -------------------------
# Konfiguration
# -------------------------
MQTT_BROKER = os.environ.get("MQTT_BROKER", "<<MQTTHOST>>")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 8883))
MQTT_TOPIC_SENSORS = os.environ.get("MQTT_TOPIC_SENSORS", "miflora/#")
MQTT_TOPIC_ANNOUNCE = os.environ.get("MQTT_TOPIC_ANNOUNCE", "miflora/$announce")
MQTT_TOPIC_PUMP = os.environ.get("MQTT_TOPIC_PUMP", "pump/status")
MQTT_CLIENT_ID = os.environ.get("MQTT_CLIENT_ID", "mqtt_to_pg_client")
MQTT_TLS_CA = os.environ.get("MQTT_TLS_CA", "<<path-to-mosquitto-ca.crt>>")
MQTT_TLS_CERT = os.environ.get("MQTT_TLS_CERT", "<<path-to-mosquitto-client.crt>>")
MQTT_TLS_KEY = os.environ.get("MQTT_TLS_KEY", "<<path-to-mosquitto-client.key>>")

PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_USER = os.environ.get("PG_USER", "<<user>>")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "<<pass>>")
PG_DATABASE = os.environ.get("PG_DATABASE", "<<db>>")
PG_PORT = int(os.environ.get("PG_PORT", 5432))

# Optional: WhatsApp Benachrichtigung über CallMeBot
WHATSAPP_API_KEY = os.environ.get("WHATSAPP_API_KEY", "<<apikey>>")
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER", "<<number>>")

# -------------------------
# Globale Variablen
# -------------------------
# Cache für MAC-Adressen aus $announce-Nachrichten
mac_cache = {}

# -------------------------
# Datenbankverbindung
# -------------------------
def connect_db():
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            user=PG_USER,
            password=PG_PASSWORD,
            dbname=PG_DATABASE,
            port=PG_PORT
        )
        return conn
    except psycopg2.Error as err:
        print(f"❌ Fehler bei der PostgreSQL-Verbindung: {err}")
        return None

# -------------------------
# WhatsApp Nachricht senden (über CallMeBot)
# -------------------------
def send_whatsapp_message(message):
    url = f"https://api.callmebot.com/whatsapp.php?phone={WHATSAPP_NUMBER}&text={message}&apikey={WHATSAPP_API_KEY}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("✅ WhatsApp-Benachrichtigung gesendet!")
        else:
            print(f"❌ Fehler beim Senden der WhatsApp-Nachricht: {response.text}")
    except Exception as e:
        print(f"❌ Fehler beim Senden der WhatsApp-Nachricht: {e}")

# -------------------------
# MQTT-Nachrichtenverarbeitung
# -------------------------
def handle_announce(payload):
    try:
        data = json.loads(payload)
        for sensor, details in data.items():
            # Speichere den Sensor (Key: Name) und die zugehörige MAC-Adresse
            mac_cache[sensor] = details.get("mac", "00:00:00:00:00:00")
            print(f"📡 MAC-Adresse gespeichert: {sensor} -> {mac_cache[sensor]}")
    except json.JSONDecodeError as e:
        print(f"❌ Fehler beim Parsen von $announce JSON: {e}")

def handle_sensor_data(topic, payload):
    try:
        data = json.loads(payload)
        # Erwartete Schlüssel: moisture und temperature
        if "moisture" in data and "temperature" in data:
            # Extrahiere den Sensor-Namen aus dem Topic (z. B. "miflora/CalatheaWohnzimmer")
            sensor_name = topic.split("/")[-1]
            # Hole die MAC-Adresse aus dem Cache, falls vorhanden
            mac_address = data.get("mac_address")
#            mac_address = mac_cache.get(sensor_name, "00:00:00:00:00:00")
            moisture = data.get("moisture")
            temperature = data.get("temperature")
            light = data.get("light", None)
            conductivity = data.get("conductivity", None)
            battery = data.get("battery", None)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"🌱 Sensor: {sensor_name} | MAC: {mac_address} | Feuchtigkeit: {moisture}%, Temperatur: {temperature}°C")
            conn = connect_db()
            if conn:
                cursor = conn.cursor()
                # In sensor_data speichern wir nur die MAC-Adresse und die Messwerte, nicht den Namen
                sql = """
                    INSERT INTO sensor_data 
                    (mac_address, moisture, temperature, light, conductivity, battery, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (mac_address, moisture, temperature, light, conductivity, battery, timestamp))
                conn.commit()
                cursor.close()
                conn.close()
                print("✅ Sensordaten erfolgreich in die DB geschrieben!")
            else:
                print("❌ Verbindung zur DB fehlgeschlagen!")
        else:
            print("❌ Ungültige Sensordaten, erwartete Schlüssel fehlen.")
    except json.JSONDecodeError as e:
        print(f"❌ JSON-Fehler bei Sensordaten: {e}")
    except Exception as e:
        print(f"❌ Unerwarteter Fehler in handle_sensor_data: {e}")

def handle_pump_status(payload):
    try:
        data = json.loads(payload)
        status = data.get("status")
        timestamp = data.get("timestamp", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print(f"💧 Pumpenstatus: {status} um {timestamp}")
        conn = connect_db()
        if conn:
            cursor = conn.cursor()
            sql = "INSERT INTO pump_log (status, timestamp) VALUES (%s, %s)"
            cursor.execute(sql, (status, timestamp))
            conn.commit()
            cursor.close()
            conn.close()
            print("✅ Pumpenstatus in die DB geschrieben!")
            if status == "ON":
                send_whatsapp_message(f"💦 Pumpe gestartet um {timestamp}!")
            elif status == "OFF":
                send_whatsapp_message(f"✅ Pumpe gestoppt um {timestamp}!")
        else:
            print("❌ DB-Verbindung fehlgeschlagen!")
    except json.JSONDecodeError as e:
        print(f"❌ JSON-Fehler bei Pumpenstatus: {e}")
    except Exception as e:
        print(f"❌ Unerwarteter Fehler in handle_pump_status: {e}")

# -------------------------
# MQTT Callback Funktionen
# -------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT-Verbindung hergestellt!")
        client.subscribe(MQTT_TOPIC_SENSORS)
        client.subscribe(MQTT_TOPIC_ANNOUNCE)
        client.subscribe(MQTT_TOPIC_PUMP)
    else:
        print("❌ MQTT-Verbindungsfehler, rc =", rc)

def on_connection_lost(client, userdata, rc):
    print("❌ Verbindung zum MQTT-Broker verloren. Code:", rc)
    # Versuche, die Verbindung wiederherzustellen
    try:
        client.reconnect()
        print("🔄 Wiederverbindung erfolgreich!")
    except Exception as e:
        print("❌ Fehler bei der Wiederverbindung:", e)


def on_message(client, userdata, message):
    payload = message.payload.decode("utf-8")
    topic = message.topic
    if topic == MQTT_TOPIC_ANNOUNCE:
        handle_announce(payload)
    elif topic.startswith("miflora/"):
        handle_sensor_data(topic, payload)
    elif topic == MQTT_TOPIC_PUMP:
        handle_pump_status(payload)

# -------------------------
# Hauptfunktion
# -------------------------
def main():
    client = mqtt.Client(MQTT_CLIENT_ID)
    client.on_connect = on_connect
    client.on_connection_lost = on_connection_lost
    client.on_message = on_message
    # TLS konfigurieren
    client.tls_set(ca_certs=MQTT_TLS_CA, certfile=MQTT_TLS_CERT, keyfile=MQTT_TLS_KEY)
    try:
        client.connect(MQTT_BROKER, MQTT_PORT)
        print(f"📡 Verbunden mit MQTT-Broker {MQTT_BROKER}")
        client.loop_forever()
    except Exception as e:
        print(f"❌ Fehler beim Verbinden mit MQTT: {e}")

if __name__ == "__main__":
    main()