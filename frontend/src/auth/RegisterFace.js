import React, { useRef, useState } from "react";
import { ref, uploadString } from "firebase/storage";
import { storage } from "../firebase";

function RegisterFace({ userId, onUploaded }) {
  const videoRef = useRef();
  const [loaded, setLoaded] = useState(false);

  const startCamera = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    videoRef.current.srcObject = stream;
    setLoaded(true);
  };

  const captureFace = async () => {
    const canvas = document.createElement("canvas");
    canvas.width = 320;
    canvas.height = 320;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(videoRef.current, 0, 0, 320, 320);

    const imgData = canvas.toDataURL("image/jpeg");

    // Upload facial template
    await uploadString(ref(storage, `faces/${userId}.jpg`), imgData, "data_url");

    alert("Face Registered Successfully!");
    onUploaded();
  };

  return (
    <div>
      <h2>Register Face</h2>
      <video ref={videoRef} autoPlay width="320" />

      {!loaded && <button onClick={startCamera}>Start Camera</button>}
      {loaded && <button onClick={captureFace}>Capture & Save</button>}
    </div>
  );
}

export default RegisterFace;
