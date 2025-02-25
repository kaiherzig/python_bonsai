// routes/sensordata.js
const express = require("express");
const router = express.Router();
const pool = require("../db");
const { DateTime } = require("luxon");

router.get("/api/sensordaten", (req, res) => {
  let zeitraum = req.query.zeitraum || "1 DAY";
  const sensor = req.query.sensor || "Alle"; // entweder "Alle" oder MAC-Adresse

  const allowedIntervals = [
    "15 MINUTE", "30 MINUTE", "1 HOUR", "6 HOUR",
    "1 DAY", "7 DAY", "14 DAY", "30 DAY", "180 DAY", "365 DAY",
  ];
  if (!allowedIntervals.includes(zeitraum)) {
    zeitraum = "1 DAY";
  }

  let sql;
  let params = [];
  if (sensor === "Alle") {
    sql = `
      SELECT sm.name AS sensor_name,
             sm.zimmer,
             sm.mac AS sensor_mac,
             sd.timestamp,
             sd.moisture,
             sd.temperature,
             sd.light,
             sd.conductivity,
             sd.battery
      FROM sensor_data sd
      JOIN sensor_meta sm ON sd.mac_address = sm.mac
      WHERE sd.timestamp >= NOW() - INTERVAL '${zeitraum}'
      ORDER BY sm.mac, sd.timestamp ASC;
    `;
  } else {
    sql = `
      SELECT sm.name AS sensor_name,
             sm.zimmer,
             sd.timestamp,
             sd.moisture,
             sd.temperature,
             sd.light,
             sd.conductivity,
             sd.battery
      FROM sensor_data sd
      JOIN sensor_meta sm ON sd.mac_address = sm.mac
      WHERE sd.timestamp >= NOW() - INTERVAL '${zeitraum}'
        AND LOWER(sm.mac) = LOWER($1)
      ORDER BY sd.timestamp ASC;
    `;
    params.push(sensor);
  }
  pool.query(sql, params, (err, result) => {
    if (err) {
      console.error("❌ SQL-Fehler:", err.message);
      return res.status(500).json({ error: "Fehler beim Abrufen der Daten", details: err.message });
    }
    res.json(result.rows);
  });
});

// Optional: Endpoint für die letzten Messwerte
router.get("/api/letzte-messwerte", (req, res) => {
  const sensor = req.query.sensor || "Alle";
  const { DateTime } = require("luxon");

  if (sensor === "Alle") {
    const sql = `
      SELECT 
          sm.name AS sensor_name,
          sm.zimmer,
          sm.mac AS sensor_mac,
          sd.moisture,
          sd.temperature,
          sd.light,
          sd.conductivity,
          sd.battery,
          sd.timestamp,
          (SELECT COUNT(*) FROM sensor_data WHERE mac_address = sm.mac) AS data_count
      FROM sensor_meta sm
      LEFT JOIN LATERAL (
          SELECT *
          FROM sensor_data
          WHERE mac_address = sm.mac
          ORDER BY timestamp DESC
          LIMIT 1
      ) sd ON true
      ORDER BY sm.name;
    `;
    pool.query(sql, (err, result) => {
      if (err) {
        console.error("Fehler beim Abrufen der letzten Messwerte (Alle):", err);
        return res.status(500).json({ error: "Fehler beim Abrufen der letzten Messwerte" });
      }
      const rows = result.rows.map(row => {
        if (row.timestamp) {
          const dt = DateTime.fromJSDate(row.timestamp, { zone: "utc" });
          row.timestamp_berlin = dt.setZone("Europe/Berlin").toFormat("yyyy-LL-dd HH:mm:ss");
        } else {
          row.timestamp_berlin = "N/A";
        }
        return row;
      });
      res.json(rows);
    });
  } else {
    const sql = `
      SELECT 
             sm.name AS sensor_name,
             sm.zimmer,
             sd.moisture,
             sd.temperature,
             sd.light,
             sd.conductivity,
             sd.battery,
             sd.timestamp,
             sm.mac AS sensor_mac,
             (SELECT COUNT(*) FROM sensor_data WHERE mac_address = sm.mac) AS data_count
      FROM sensor_data sd
      JOIN sensor_meta sm ON sd.mac_address = sm.mac
      WHERE LOWER(sm.mac) = LOWER($1)
        AND sd.timestamp = (
          SELECT MAX(timestamp)
          FROM sensor_data
          WHERE mac_address = sm.mac
        )
    `;
    pool.query(sql, [sensor], (err, result) => {
      if (err) {
        console.error("Fehler beim Abrufen der letzten Messwerte:", err);
        return res.status(500).json({ error: "Fehler beim Abrufen der letzten Messwerte" });
      }
      if (result.rows.length > 0) {
        const row = result.rows[0];
        const dt = DateTime.fromJSDate(row.timestamp, { zone: "utc" });
        row.timestamp_berlin = dt.setZone("Europe/Berlin").toFormat("yyyy-LL-dd HH:mm:ss");
        res.json(row);
      } else {
        res.json({});
      }
    });
  }
});

module.exports = router;
