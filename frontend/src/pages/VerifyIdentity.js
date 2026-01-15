import React, { useEffect, useRef, useState } from "react";
import { getReferencePhoto } from "../firebase/storage";
import verifyFaceMatch from "../proctoring/faceVerify";
import { socket } from "../proctoring/socket";

function VerifyIdentity({ userId, sessionId, onVerified }) {
  const videoRef = useRef(null);
  const [status, setStatus] = useState("Waiting for camera...");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    startCamera();
  }, []);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      videoRef.current.srcObject = stream;
      setStatus("Camera Active");
      setLoading(false);
    } catch (err) {
      alert("Camera access required");
    }
  };

  const handleVerify = async () => {
    setStatus("Fetching reference photo...");
    const referenceImage = await getReferencePhoto(userId);

    setStatus("Comparing faces...");
    const result = await verifyFaceMatch(videoRef.current, referenceImage);

    if (result.match) {
      setStatus("Identity Verified ✔");

      socket.emit("identity-verified", {
        sessionId,
        userId,
        confidence: result.confidence
      });

      setTimeout(() => onVerified(), 800);
    } else {
      setStatus("Identity Verification Failed ❌ (Try Again)");
    }
  };

  return (
    <div style={{ padding: 30 }}>
      <h2>Identity Verification</h2>

      <video
        ref={videoRef}
        autoPlay
        style={{ width: "300px", border: "2px solid #333", borderRadius: 8 }}
      />

      <p>{status}</p>

      <button
        onClick={handleVerify}
        disabled={loading}
        style={{ padding: "10px 20px", marginTop: 20 }}
      >
        Verify My Face
      </button>
    </div>
  );
}

export default VerifyIdentity;
