const { DataTypes } = require('sequelize');
const { sequelize } = require('../config/database');

const SessionParticipant = sequelize.define('SessionParticipant', {
  id: {
    type: DataTypes.UUID,
    defaultValue: DataTypes.UUIDV4,
    primaryKey: true
  },
  sessionId: {
    type: DataTypes.UUID,
    allowNull: false,
    references: {
      model: 'Sessions',
      key: 'id'
    }
  },
  studentId: {
    type: DataTypes.UUID,
    allowNull: false,
    references: {
      model: 'Users',
      key: 'id'
    }
  },
  joinedAt: {
    type: DataTypes.DATE,
    allowNull: true
  },
  leftAt: {
    type: DataTypes.DATE,
    allowNull: true
  },
  faceVerified: {
    type: DataTypes.BOOLEAN,
    defaultValue: false
  },
  faceVerificationScore: {
    type: DataTypes.FLOAT,
    allowNull: true
  },
  recordingUrl: {
    type: DataTypes.STRING,
    allowNull: true
  },
  status: {
    type: DataTypes.ENUM('invited', 'joined', 'left', 'removed'),
    defaultValue: 'invited'
  }
});

module.exports = SessionParticipant;


