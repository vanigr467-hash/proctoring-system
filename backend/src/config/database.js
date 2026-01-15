// ...existing code...
const { Sequelize } = require('sequelize');
const logger = require('../utils/logger');

const sequelize = new Sequelize(
  process.env.DB_NAME || 'proctoring',
  process.env.DB_USER || 'postgres',
  process.env.DB_PASSWORD || '',
  {
    host: process.env.DB_HOST || 'localhost',
    port: process.env.DB_PORT ? parseInt(process.env.DB_PORT, 10) : 5432,
    dialect: 'postgres',
    logging: (msg) => (logger && logger.debug ? logger.debug(msg) : console.debug(msg)),
    pool: {
      max: 20,
      min: 5,
      acquire: 30000,
      idle: 10000,
    },
  }
);

const connectDB = async () => {
  try {
    await sequelize.authenticate();
    logger?.info('Database connection established successfully');
    // follow repo convention: sync with alter in dev
    await sequelize.sync({ alter: true });
    logger?.info('Database models synchronized');
  } catch (error) {
    logger?.error('Unable to connect to database:', error);
    throw error;
  }
};

module.exports = { sequelize, connectDB };
// ...existing code...