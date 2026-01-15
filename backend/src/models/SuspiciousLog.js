const { DataTypes } = require("sequelize");
const { sequelize } = require("../config/database");

const SuspiciousLog = sequelize.define("SuspiciousLog", {
  sessionId: { type: DataTypes.STRING },
  userId: { type: DataTypes.STRING },
  type: { type: DataTypes.STRING },           // example: "phone detected"
  timestamp: { type: DataTypes.DATE },
});

module.exports = SuspiciousLog;
