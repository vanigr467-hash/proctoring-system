const Session = require("../models/Session");
const SessionParticipant = require("../models/SessionParticipant");
const ActivityLog = require("../models/ActivityLog");
const logger = require("../utils/logger");

// Create a new exam session
exports.createSession = async (req, res) => {
  try {
    const { title, subject, facultyId, startTime, endTime } = req.body;

    const newSession = await Session.create({
      title,
      subject,
      facultyId,
      startTime,
      endTime,
      status: "scheduled",
    });

    logger.info("Session created successfully");

    res.status(201).json({
      success: true,
      session: newSession,
    });
  } catch (error) {
    logger.error("Error creating session:", error);
    res.status(500).json({ success: false, message: "Failed to create session" });
  }
};

// Join session (student or faculty)
exports.joinSession = async (req, res) => {
  try {
    const { sessionId, userId, role } = req.body;

    const session = await Session.findByPk(sessionId);
    if (!session) {
      return res.status(404).json({ success: false, message: "Session not found" });
    }

    const participant = await SessionParticipant.create({
      sessionId,
      userId,
      role,
      joinedAt: new Date(),
    });

    logger.info(`User ${userId} joined session ${sessionId}`);

    res.status(200).json({
      success: true,
      participant,
    });
  } catch (error) {
    logger.error("Error joining session:", error);
    res.status(500).json({ success: false, message: "Failed to join session" });
  }
};

// Get full session details (participants + logs)
exports.getSessionDetails = async (req, res) => {
  try {
    const { sessionId } = req.params;

    const session = await Session.findByPk(sessionId, {
      include: [SessionParticipant, ActivityLog],
    });

    if (!session) {
      return res.status(404).json({ success: false, message: "Session not found" });
    }

    res.status(200).json({
      success: true,
      session,
    });
  } catch (error) {
    logger.error("Error fetching session details:", error);
    res.status(500).json({ success: false, message: "Failed to fetch session details" });
  }
};

// End session
exports.endSession = async (req, res) => {
  try {
    const { sessionId } = req.body;

    const session = await Session.findByPk(sessionId);
    if (!session) {
      return res.status(404).json({ success: false, message: "Session not found" });
    }

    session.status = "completed";
    session.endTime = new Date();
    await session.save();

    logger.info(`Session ${sessionId} ended`);

    res.status(200).json({
      success: true,
      message: "Session ended successfully",
    });
  } catch (error) {
    logger.error("Error ending session:", error);
    res.status(500).json({ success: false, message: "Failed to end session" });
  }
};
