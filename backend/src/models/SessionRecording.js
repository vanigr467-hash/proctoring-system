const { DataTypes } = require("sequelize");
const { sequelize } = require("../config/database");

const SessionRecording = sequelize.define("SessionRecording", {
  sessionId: DataTypes.STRING,
  userId: DataTypes.STRING,
  url: DataTypes.STRING,
});

module.exports = SessionRecording;
