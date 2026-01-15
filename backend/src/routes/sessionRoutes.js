const express = require("express");
const router = express.Router();
const { logSuspicious, getSessionLogs } = require("../controllers/sessionController");

router.post("/log", logSuspicious);
router.get("/logs/:sessionId", getSessionLogs);

module.exports = router;
