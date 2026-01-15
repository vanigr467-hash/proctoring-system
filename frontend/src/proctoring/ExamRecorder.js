import React, { useEffect, useRef, useState } from "react";
import { ref, uploadBytes, getDownloadURL } from "firebase/storage";
import { storage } from "../firebaseConfig";
import axios from "axios";
import io from "socket.io-client";

const socket = io(process.env.REACT_APP_SOCKET_URL);

function ExamRecorder({ userId, sessionId, onRecordingComplete }) {
  const videoRef = useRef();
  const mediaRecorder = useRef();
  const [chunks, setChunks] = useState([]);
  const [recording, setRecording] = useState(false);

  useEffect(() => {
    startCamera();
  }, []);

  const startCamera = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    videoRef.current.srcObject = stream;

    mediaRecorder.current = new MediaRecorder(stream, { mimeType: "video/webm" });

    mediaRecorder.current.ondataavailable = (e) => {
      setChunks((prev) => [...prev, e.data]);
    };

    mediaRecorder.current.onstop = handleUpload;

    mediaRecorder.current.start(1000); // record chunks each second
    setRecording(true);
  };

  const handleUpload = async () => {
    const blob = new Blob(chunks, { type: "video/webm" });

    const storageRef = ref(storage, `recordings/${sessionId}-${userId}.webm`);
    await uploadBytes(storageRef, blob);

    const downloadURL = await getDownloadURL(storageRef);

    // Save in backend
    await axios.post(`${process.env.REACT_APP_API_URL}/recording/save`, {
      sessionId,
      userId,
      url: downloadURL,
    });

    onRecordingComplete(downloadURL);
  };

  const stopRecording = () => {
    mediaRecorder.current.stop();
    setRecording(false);

    socket.emit("exam-ended", { userId, sessionId });
  };

  return (
    <div>
      <video ref={videoRef} autoPlay width={350} />
      {recording && (
        <button onClick={stopRecording} style={{ marginTop: "20px" }}>
          Stop Recording
        </button>
      )}
    </div>
  );
}

export default ExamRecorder;
