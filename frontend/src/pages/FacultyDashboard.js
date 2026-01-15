import React, { useEffect, useRef, useState } from "react";
import { socket } from "../proctoring/socket";
import StudentTile from "../components/StudentTile";
import axios from "axios";
import { Typography } from "@mui/material";

function FacultyLiveDashboard({ sessionId }) {
  const [participants, setParticipants] = useState([]);
  const [videos, setVideos] = useState({});
  const [screens, setScreens] = useState({});
  const [alerts, setAlerts] = useState({});

  useEffect(() => {
    socket.emit("join-room", {
      sessionId,
      role: "faculty",
      userId: "faculty-dashboard",
    });

    socket.on("participant-update", (data) => {
      setParticipants((prev) => {
        const others = prev.filter((p) => p.userId !== data.userId);
        return [...others, data];
      });
    });

    socket.on("render-video", ({ userId, chunk }) => {
      const video = videos[userId];
      if (video) {
        const blob = new Blob([chunk], { type: "video/webm" });
        video.src = URL.createObjectURL(blob);
      }
    });

    socket.on("faculty-alert", (data) => {
      setAlerts((prev) => ({
        ...prev,
        [data.userId]: [...(prev[data.userId] || []), data.type],
      }));
    });

    socket.on("render-screen", ({ userId, screen }) => {
      const vid = screens[userId];
      if (vid) {
        const blob = new Blob([screen], { type: "video/webm" });
        vid.src = URL.createObjectURL(blob);
      }
    });
  }, [sessionId, videos, screens]);

  return (
    <div style={{ padding: 20 }}>
      <Typography variant="h4">Live Monitoring — Session {sessionId}</Typography>

      <div style={{ display: "flex", flexWrap: "wrap" }}>
        {participants.map((p) => (
          <StudentTile
            key={p.userId}
            user={p}
            videoRef={(el) => (videos[p.userId] = el)}
            screenRef={(el) => (screens[p.userId] = el)}
            alerts={alerts[p.userId] || []}
          />
        ))}
      </div>
    </div>
  );
}

export default FacultyLiveDashboard;
