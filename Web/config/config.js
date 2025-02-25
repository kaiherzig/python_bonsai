// config/config.js
module.exports = {
  PORT: process.env.PORT || 3000,
  PG_HOST: process.env.PG_HOST || "localhost",
  PG_USER: process.env.PG_USER || "<<user>>",
  PG_PASSWORD: process.env.PG_PASSWORD || "<<pass>>",
  PG_DATABASE: process.env.PG_DATABASE || "<<db>>",
  PG_PORT: process.env.PG_PORT || 5432,
  MQTT_BROKER: process.env.MQTT_BROKER || "<<mqtthost>>",
  MQTT_PORT: process.env.MQTT_PORT || 8883,
  MQTT_TOPIC_SENSORS: process.env.MQTT_TOPIC_SENSORS || "miflora/#",
  MQTT_TOPIC_ANNOUNCE: process.env.MQTT_TOPIC_ANNOUNCE || "miflora/$announce",
  MQTT_TOPIC_PUMP: process.env.MQTT_TOPIC_PUMP || "pump/status",
  MQTT_CLIENT_ID: process.env.MQTT_CLIENT_ID || "miflora_pg_client",
  MQTT_TLS_CA: process.env.MQTT_TLS_CA || "<<path-to-mosquitto-ca.crt>>",
  MQTT_TLS_CERT: process.env.MQTT_TLS_CERT || "<<path-to-mosquitto-client.crt>>",
  MQTT_TLS_KEY: process.env.MQTT_TLS_KEY || "<<path-to-mosquitto-client.key>>",
};
