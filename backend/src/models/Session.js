// ...existing code...
const { DataTypes } = require("sequelize");
const { sequelize } = require("../config/database");

const Session = sequelize.define(
  "Session",
  {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true,
    },
    title: {
      type: DataTypes.STRING,
      allowNull: false,
    },
    sessionCode: {
      type: DataTypes.STRING,
      unique: true,
      allowNull: false,
    },
    facultyId: {
      type: DataTypes.UUID,
      allowNull: false,
    },
    status: {
      type: DataTypes.ENUM("upcoming", "running", "ended"),
      defaultValue: "upcoming",
    },
    startTime: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    endTime: {
      type: DataTypes.DATE,
      allowNull: true,
    },
  },
  {
    tableName: "Sessions",
    timestamps: true,
  }
);

module.exports = Session;
// ...existing code...