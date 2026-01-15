import React, { useEffect, useRef } from "react";
import * as faceapi from "face-api.js";
import { detectPhone, loadPhoneModel } from "../utils/phoneDetector";
import io from "socket.io-client";

const socket = io(process.env.REACT_APP_SOCKET_URL);

function ExamMonitor({ userId, sessionId }) {
  const videoRef = useRef();

  useEffect(() => {
    init();
  }, []);

  const init = async () => {
    await faceapi.nets.tinyFaceDetector.loadFromUri("/models");
    await faceapi.nets.faceLandmark68Net.loadFromUri("/models");
    await faceapi.nets.faceRecognitionNet.loadFromUri("/models");

    await loadPhoneModel();

    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    videoRef.current.srcObject = stream;

    monitorSuspicious();
  };

  const sendAlert = (type) => {
    socket.emit("suspicious", {
      type,
      userId,
      sessionId,
      timestamp: Date.now(),
    });
  };

  const monitorSuspicious = async () => {
    setInterval(async () => {
      const detections = await faceapi
        .detectAllFaces(videoRef.current, new faceapi.TinyFaceDetectorOptions())
        .withFaceLandmarks();

      if (detections.length === 0) {
        sendAlert("No face detected");
        return;
      }

      if (detections.length > 1) {
        sendAlert("Multiple persons detected");
      }

      const phoneDetected = await detectPhone(videoRef.current);
      if (phoneDetected) sendAlert("Phone detected");

      const landmarks = detections[0].landmarks;
      const leftEye = landmarks.getLeftEye();
      const rightEye = landmarks.getRightEye();
      const avgX = [...leftEye, ...rightEye].reduce((a, b) => a + b.x, 0) / 12;

      const faceCenter = detections[0].detection.box.x + detections[0].detection.box.width / 2;

      if (Math.abs(avgX - faceCenter) > 40) {
        sendAlert("Looking away from screen");
      }
    }, 2000);
  };

  return (
    <div>
      <h3>Monitoring Student</h3>
      <video ref={videoRef} autoPlay width={350} />
    </div>
  );
}

export default ExamMonitor;
