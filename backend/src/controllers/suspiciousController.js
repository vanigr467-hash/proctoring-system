const SuspiciousLog = require("../models/SuspiciousLog");

exports.addLog = async (req, res) => {
  const { sessionId, userId, type, timestamp } = req.body;

  await SuspiciousLog.create({
    sessionId,
    userId,
    type,
    timestamp,
  });

  return res.json({ success: true });
};

exports.getSessionLogs = async (req, res) => {
  const { sessionId } = req.params;

  const logs = await SuspiciousLog.findAll({
    where: { sessionId },
    order: [["timestamp", "ASC"]],
  });

  // Generate report text automatically
  const summary = generateSummary(logs);

  res.json({
    sessionId,
    logs,
    summary,
  });
};

function generateSummary(logs) {
  if (!logs.length) {
    return "No suspicious activity detected during the exam. The student maintained compliance throughout the session.";
  }

  let report = "Suspicious activities were detected during the exam session:\n\n";

  const counts = {};
  logs.forEach((log) => {
    counts[log.type] = (counts[log.type] || 0) + 1;
  });

  for (let key in counts) {
    report += `• ${key}: ${counts[key]} times\n`;
  }

  report += `\nReview the timeline for detailed insights.`;

  return report;
}
