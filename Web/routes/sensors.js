// routes/sensors.js
const express = require("express");
const router = express.Router();
const pool = require("../db");

router.get("/api/sensors", (req, res) => {
  const sql = "SELECT name, zimmer, mac FROM sensor_meta";
  pool.query(sql, (err, result) => {
    if (err) {
      console.error("Fehler beim Abrufen der Sensoren:", err);
      return res.status(500).json({ error: "Fehler beim Abrufen der Sensoren" });
    }
    res.json(result.rows);
  });
});

module.exports = router;
