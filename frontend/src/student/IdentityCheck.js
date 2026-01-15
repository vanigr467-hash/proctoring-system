import React, { useEffect, useRef, useState } from "react";
import * as faceapi from "face-api.js";
import { storage } from "../firebase";
import { getDownloadURL, ref } from "firebase/storage";

function IdentityCheck({ userId, onVerified }) {
  const videoRef = useRef();
  const [status, setStatus] = useState("Loading models...");

  useEffect(() => {
    (async () => {
      await faceapi.nets.tinyFaceDetector.loadFromUri("/models");
      await faceapi.nets.faceRecognitionNet.loadFromUri("/models");
      await faceapi.nets.faceLandmark68Net.loadFromUri("/models");

      setStatus("Starting camera...");
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      videoRef.current.srcObject = stream;

      const url = await getDownloadURL(ref(storage, `faces/${userId}.jpg`));
      const img = await faceapi.fetchImage(url);

      const reference = await faceapi
        .detectSingleFace(img)
        .withFaceLandmarks()
        .withFaceDescriptor();

      // Start live matching loop
      const interval = setInterval(async () => {
        const live = await faceapi
          .detectSingleFace(videoRef.current, new faceapi.TinyFaceDetectorOptions())
          .withFaceLandmarks()
          .withFaceDescriptor();

        if (live && reference) {
          const distance = faceapi.euclideanDistance(reference.descriptor, live.descriptor);

          if (distance < 0.45) {
            setStatus("Identity Verified ✔");
            clearInterval(interval);
            onVerified();
          } else {
            setStatus("Face mismatch ❌");
          }
        }
      }, 1000);
    })();
  }, []);

  return (
    <div>
      <h2>Identity Verification</h2>
      <video ref={videoRef} autoPlay width="320" />
      <p>{status}</p>
    </div>
  );
}

export default IdentityCheck;
