import React from "react";
import ExamMonitor from "../proctoring/ExamMonitor";
import ExamRecorder from "../proctoring/ExamRecorder";

function StartExam({ userId, sessionId }) {
  const handleComplete = (url) => {
    alert("Recording uploaded successfully!");
  };

  return (
    <div>
      <h1>Exam Started</h1>
      <ExamMonitor userId={userId} sessionId={sessionId} />
      <ExamRecorder userId={userId} sessionId={sessionId} onRecordingComplete={handleComplete} />
    </div>
  );
}

export default StartExam;
