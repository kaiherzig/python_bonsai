// server.js
const express = require("express");
const app = express();
const config = require("./config/config");
const PORT = config.PORT || 3000;

// Statische Dateien
app.use(express.static("public"));

// Routen importieren
const sensorsRouter = require("./routes/sensors");
const sensordataRouter = require("./routes/sensordata");
const pumpRouter = require("./routes/pump");

// Routen verwenden
app.use(sensorsRouter);
app.use(sensordataRouter);
app.use(pumpRouter);

app.listen(PORT, () => {
  console.log(`Server läuft unter http://localhost:${PORT}`);
});
