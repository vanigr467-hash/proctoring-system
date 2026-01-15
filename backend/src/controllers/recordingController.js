const SessionRecording = require("../models/SessionRecording");

exports.saveRecording = async (req, res) => {
  const { sessionId, userId, url } = req.body;

  await SessionRecording.create({
    sessionId,
    userId,
    url,
  });

  res.json({ success: true });
};

exports.getRecording = async (req, res) => {
  const { sessionId } = req.params;

  const files = await SessionRecording.findAll({ where: { sessionId } });

  res.json(files);
};
