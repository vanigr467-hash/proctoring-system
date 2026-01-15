const express = require("express");
const router = express.Router();
const Session = require("../models/Session");
const SessionParticipant = require("../models/SessionParticipant");

router.get("/:sessionId", async (req, res) => {
  const { sessionId } = req.params;

  const session = await Session.findOne({ where: { sessionId } });
  const participants = await SessionParticipant.findAll({ where: { sessionId } });

  res.json({
    session,
    participants,
  });
});

module.exports = router;
