const express = require("express");
const router = express.Router();
const { saveRecording, getRecording } = require("../controllers/recordingController");

router.post("/save", saveRecording);
router.get("/:sessionId", getRecording);

module.exports = router;
