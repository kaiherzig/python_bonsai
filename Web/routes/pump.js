// routes/pump.js
const express = require("express");
const router = express.Router();
const pool = require("../db");
const { DateTime } = require("luxon");

router.get("/api/pump_status", (req, res) => {
  const sql = "SELECT status, timestamp FROM pump_log ORDER BY timestamp DESC LIMIT 1";
  pool.query(sql, (err, result) => {
    if (err) {
      console.error("Fehler beim Abrufen des Pumpenstatus:", err.message);
      return res.status(500).json({ error: "Fehler beim Abrufen des Pumpenstatus" });
    }
    let pump_status = "❌ Keine Gieß-Aktion erkannt";
    if (result.rows.length > 0) {
      const row = result.rows[0];
      const utcTime = DateTime.fromJSDate(row.timestamp, { zone: "utc" });
      const berlinTime = utcTime.setZone("Europe/Berlin");
      const formattedTime = berlinTime.toFormat("yyyy-LL-dd HH:mm:ss");
      if (row.status === "ON") {
        pump_status = "💦 Pumpe AKTIV seit " + formattedTime;
      } else {
        pump_status = "✅ Letztes Gießen beendet: " + formattedTime;
      }
    }
    res.json({ status: pump_status });
  });
});

module.exports = router;
