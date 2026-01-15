export default async function detectSuspiciousActivity(videoRef) {
  const video = videoRef.current;
  if (!video) return null;

  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d");

  canvas.width = 300;
  canvas.height = 200;

  ctx.drawImage(video, 0, 0, 300, 200);

  // RULE 1 — No face detected (too dark or moved away)
  if (Math.random() < 0.1) {
    return {
      type: "No Face Detected",
      severity: "high"
    };
  }

  // RULE 2 — Multiple faces (simple random simulation)
  if (Math.random() < 0.05) {
    return {
      type: "Multiple Faces Detected",
      severity: "critical"
    };
  }

  // RULE 3 — Looking away
  if (Math.random() < 0.1) {
    return {
      type: "Head Turned Away",
      severity: "medium"
    };
  }

  return null;
}
