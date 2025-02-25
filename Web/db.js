// db.js
const { Pool } = require("pg");
const config = require("./config/config");

const pool = new Pool({
  host: config.PG_HOST,
  user: config.PG_USER,
  password: config.PG_PASSWORD,
  database: config.PG_DATABASE,
  port: config.PG_PORT,
});

pool.query("SELECT NOW()", (err, res) => {
  if (err) {
    console.error("❌ Fehler bei der PostgreSQL-Verbindung:", err.message);
  } else {
    console.log("✅ Erfolgreich mit PostgreSQL verbunden! Serverzeit:", res.rows[0].now);
  }
});

module.exports = pool;
