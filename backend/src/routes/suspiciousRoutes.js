const express = require("express");
const router = express.Router();
const { addLog, getSessionLogs } = require("../controllers/suspiciousController");

router.post("/add", addLog);
router.get("/:sessionId", getSessionLogs);

module.exports = router;
