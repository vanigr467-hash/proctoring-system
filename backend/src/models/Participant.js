const { DataTypes } = require("sequelize");
const { sequelize } = require("../config/db");

const Participant = sequelize.define("Participant", {
  id: {
    type: DataTypes.UUID,
    defaultValue: DataTypes.UUIDV4,
    primaryKey: true,
  },

  sessionId: {
    type: DataTypes.UUID,
    allowNull: false,
  },

  studentId: {
    type: DataTypes.UUID,
    allowNull: false,
  },

  joinedAt: {
    type: DataTypes.DATE,
    defaultValue: Data.now,
  },

  status: {
    type: DataTypes.ENUM("active", "left"),
    defaultValue: "active",
  }
});

module.exports = Participant;
