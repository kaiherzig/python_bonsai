# 🌿 Bonsai Automatisches Bewässerungssystem (B.A.W.S.) 🚀

Dieses Projekt ist ein automatisches Bonsai-Bewässerungssystem, das mit einem **MiFlora-Pflanzensensor**, **MQTT** und einem **Raspberry Pi** arbeitet.  
Die Bewässerung wird automatisch gesteuert und erfolgt nur, wenn die gemessene Feuchtigkeit unter einen bestimmten Wert fällt.  

## 📌 **Übersicht**
- 💧 **Feuchtigkeitssensor** (MiFlora) misst den Feuchtigkeitsgehalt der Erde.
- 📡 **miflora-mqtt-daemon** sendet Sensordaten über MQTT.
- 🖥️ **Raspberry Pi** empfängt die Daten und steuert das Relais für die Pumpe.
- ⚠️ **Fehlermeldung nach 3h ohne MQTT-Daten** (z. B. falls der Sensor ausfällt).

---

## 🚀 **Installation & Einrichtung**

### 1️⃣ **Raspberry Pi vorbereiten**

sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip mosquitto mosquitto-clients git -y
2️⃣ miflora-mqtt-daemon installieren
Dieser Dienst liest die Sensordaten von MiFlora und sendet sie über MQTT.

git clone https://github.com/ThomDietrich/miflora-mqtt-daemon.git
cd miflora-mqtt-daemon
sudo pip3 install -r requirements.txt

Nun die Konfiguration anpassen:

sudo nano config.ini
Folgende Parameter müssen gesetzt werden:

ini
[General]
adapter = hci0
log_level = info

[MQTT]
host = localhost
port = 1883
topic_prefix = miflora
client_id = miflora-client

[Plant:Bonsai]
mac = <<MAC>>


Dann den Service starten:

sudo systemctl enable miflora.service
sudo systemctl start miflora.service

3️⃣ Pumpen-Skript installieren
Wechsle zum /opt/-Ordner und erstelle das Verzeichnis:

sudo mkdir -p /opt/pump/
sudo chown -R $USER:$USER /opt/pump/
cd /opt/pump/

4️⃣ Pumpen-Daemon als systemd-Service einrichten
Erstelle die Datei:

sudo nano /etc/systemd/system/pump.service

[Unit]
Description=Pump Control Client/Daemon
After=network.target bluetooth.service mosquitto.service miflora.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/pump/
ExecStart=/usr/bin/python3 /opt/pump/pump.py
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=true
Restart=always

[Install]
WantedBy=multi-user.target

5️⃣ Service aktivieren und starten

sudo systemctl daemon-reload
sudo systemctl enable pump.service
sudo systemctl start pump.service