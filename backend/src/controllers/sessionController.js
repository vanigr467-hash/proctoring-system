const { v4: uuidv4 } = require("uuid");
const Session = require("../models/Session");
const Participant = require("../models/Participant");

exports.createSession = async (req, res) => {
  try {
    const { title } = req.body;
    const facultyId = req.user.id;

    const session = await Session.create({
      title,
      facultyId,
      sessionCode: uuidv4().slice(0, 6)
    });

    res.status(201).json({
      message: "Session created successfully",
      session
    });
  } catch (err) {
    console.error("CREATE SESSION ERROR:", err);
    res.status(500).json({ message: "Server error" });
  }
};


exports.joinSession = async (req, res) => {
  try {
    const { sessionCode } = req.body;
    const studentId = req.user.id;

    const session = await Session.findOne({ where: { sessionCode } });
    if (!session) return res.status(404).json({ message: "Invalid session code" });

    await Participant.create({
      sessionId: session.id,
      studentId
    });

    res.status(200).json({
      message: "Joined successfully",
      session
    });

  } catch (err) {
    console.error("JOIN SESSION ERROR:", err);
    res.status(500).json({ message: "Server error" });
  }
};


const ActivityLog = require("../models/ActivityLog");

exports.logSuspicious = async (req, res) => {
  const { sessionId, userId, type } = req.body;

  await ActivityLog.create({
    sessionId,
    userId,
    type,
    timestamp: new Date()
  });

  res.json({ success: true });
};

exports.getSessionLogs = async (req, res) => {
  const { sessionId } = req.params;

  const logs = await ActivityLog.findAll({ where: { sessionId } });

  res.json(logs);
};
