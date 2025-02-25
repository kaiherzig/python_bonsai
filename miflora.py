#!/usr/bin/env python3
import ssl
import sys
import json
import os
from time import sleep, strftime, localtime
import paho.mqtt.client as mqtt
from miflora.miflora_poller import MiFloraPoller, MI_LIGHT, MI_TEMPERATURE, MI_MOISTURE, MI_CONDUCTIVITY, MI_BATTERY
from btlewrap import BluepyBackend, BluetoothBackendException
from bluepy.btle import BTLEException
import signal
import sdnotify
# --- Timeout-Konfiguration ---
class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("Sensor poll timed out")

# Setze den Timeout-Handler (wird in poll_and_publish() vor jedem Sensor verwendet)
signal.signal(signal.SIGALRM, timeout_handler)

# --- Konfiguration (anpassen nach Bedarf) ---
MQTT_BROKER = "<<mqtthost>>"         # MQTT-Broker-Adresse
MQTT_PORT = 8883                          # Port (TLS: 8883)
MQTT_TOPIC_BASE = "miflora"               # Basis-Topic für die Veröffentlichung
MQTT_CLIENT_ID = "<<name>>"
USE_TLS = True                          # TLS aktivieren
TLS_CA = "<<path-to-mosquitto-ca.crt>>"     # CA-Zertifikat
TLS_CERT = "<<path-to-mosquitto-client.crt>>"  # Client-Zertifikat
TLS_KEY = "<<path-to-mosquitto-client.key>>"     # Client-Key

SLEEP_PERIOD = 300  # Abfrage-Intervall in Sekunden
POLL_TIMEOUT = 30   # Timeout in Sekunden für jeden Sensor-Poll

# Sensoren: Sensorname => MAC-Adresse
SENSORS = {
        "Name1": "<<MAC>>",
        "Name2": "<<MAC>>"
    # Füge hier weitere Sensoren hinzu
}
sd_notifier = sdnotify.SystemdNotifier()
sd_notifier.notify("READY=1")

# --- MQTT-Callbacks ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT connected")
    else:
        print("MQTT connection error, rc =", rc)

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("MQTT disconnected unexpectedly, rc =", rc)
        client.reconnect_delay_set(min_delay=5, max_delay=60)
        while True:
            try:
                client.reconnect()
                print("MQTT reconnected")
                break
            except Exception as e:
                print("Reconnection failed:", e)
                sleep(5)

# --- MQTT-Client initialisieren ---
mqtt_client = mqtt.Client(MQTT_CLIENT_ID)
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect

if USE_TLS:
    mqtt_client.tls_set(ca_certs=TLS_CA, certfile=TLS_CERT, keyfile=TLS_KEY, tls_version=ssl.PROTOCOL_TLS_CLIENT)

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
except Exception as e:
    print("MQTT connection failed:", e)
    sys.exit(1)
mqtt_client.loop_start()

# --- Sensordaten poll und veröffentlichen ---
def poll_and_publish():
    for sensor_name, mac in SENSORS.items():
        try:
            poller = MiFloraPoller(mac, backend=BluepyBackend, cache_timeout=SLEEP_PERIOD - 1)
            # Setze einen Alarm für den Poll-Vorgang
            signal.alarm(POLL_TIMEOUT)
            try:
                poller.fill_cache()
            finally:
                # Schalte den Alarm aus, egal ob Timeout oder Erfolg
                signal.alarm(0)
            data = {
                "mac_address": mac,
                "light": poller.parameter_value(MI_LIGHT),
                "temperature": poller.parameter_value(MI_TEMPERATURE),
                "moisture": poller.parameter_value(MI_MOISTURE),
                "conductivity": poller.parameter_value(MI_CONDUCTIVITY),
                "battery": poller.parameter_value(MI_BATTERY)
            }
            payload = json.dumps(data)
            topic = f"{MQTT_TOPIC_BASE}/{sensor_name}"
            mqtt_client.publish(topic, payload)
            print(f"Published data for {sensor_name} on topic {topic}: {payload}")
            sleep(2)  # Kurze Pause zwischen den Sensor-Polls
        except TimeoutException as te:
            print(f"Timeout polling sensor {sensor_name} ({mac}): {te}")
        except (IOError, BluetoothBackendException, BTLEException, RuntimeError, Exception) as e:
            print(f"Error polling sensor {sensor_name} ({mac}): {e}")

# --- Hauptschleife (Daemon) ---
if __name__ == "__main__":
    try:
        while True:
            poll_and_publish()
            sleep(SLEEP_PERIOD)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()