import React, { useEffect, useRef, useState } from "react";
import { socket } from "../proctoring/socket";
import startVideoStream from "../proctoring/videoSender";
import startScreenShare from "../proctoring/screenSender";
import detectSuspiciousActivity from "../proctoring/activityDetection";

function StudentExamRoom({ sessionId, userId }) {
  const videoRef = useRef(null);
  const [screenEnabled, setScreenEnabled] = useState(false);

  useEffect(() => {
    socket.emit("join-room", { sessionId, userId, role: "student" });

    // Start camera streaming
    startVideoStream(videoRef, sessionId, userId);

    // Suspicious activity detection every 2 seconds
    const interval = setInterval(async () => {
      const activity = await detectSuspiciousActivity(videoRef);
      if (activity) {
        socket.emit("suspicious-activity", {
          sessionId,
          userId,
          activity
        });
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [sessionId, userId]);

  const ToggleScreenShare = () => {
    if (!screenEnabled) {
      startScreenShare(sessionId, userId);
    }
    setScreenEnabled(!screenEnabled);
  };

  return (
    <div style={{ padding: 20 }}>
      <h2>Exam Session — {sessionId}</h2>

      <video
        ref={videoRef}
        autoPlay
        muted
        style={{ width: "300px", borderRadius: 8 }}
      />

      <div style={{ marginTop: 20 }}>
        <button onClick={ToggleScreenShare}>
          {screenEnabled ? "Stop Screen Share" : "Start Screen Share"}
        </button>
      </div>

      <p>Status: Live & Streaming</p>
    </div>
  );
}

export default StudentExamRoom;
