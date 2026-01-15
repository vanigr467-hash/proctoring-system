const { DataTypes } = require("sequelize");
const { sequelize } = require("../config/database");

const ActivityLog = sequelize.define("ActivityLog", {
  sessionId: DataTypes.STRING,
  userId: DataTypes.STRING,
  type: DataTypes.STRING,   // suspicious event
  timestamp: DataTypes.DATE
});

module.exports = ActivityLog;
