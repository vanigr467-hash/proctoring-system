import React, { useEffect, useRef } from "react";
import io from "socket.io-client";

const socket = io(process.env.REACT_APP_SOCKET_URL);

function StudentExam({ sessionId, userId }) {
  const videoRef = useRef();

  useEffect(() => {
    socket.emit("join-session", { sessionId, userId, role: "student" });

    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        videoRef.current.srcObject = stream;

        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");

        setInterval(() => {
          canvas.width = 320;
          canvas.height = 240;
          ctx.drawImage(videoRef.current, 0, 0, 320, 240);

          const frame = canvas.toDataURL("image/jpeg", 0.5);

          socket.emit("video-frame", {
            sessionId,
            studentId: userId,
            frame
          });

        }, 500); // send every 0.5 seconds

      });
  }, []);

  return (
    <div>
      <h2>Exam in Progress</h2>
      <video ref={videoRef} autoPlay playsInline width="320" />
    </div>
  );
}

export default StudentExam;

useEffect(() => {
  const checkFaceContinuously = async () => {
    const referenceUrl = await getDownloadURL(ref(storage, `faces/${userId}.jpg`));
    const faceImg = await faceapi.fetchImage(referenceUrl);

    const reference = await faceapi
      .detectSingleFace(faceImg)
      .withFaceLandmarks()
      .withFaceDescriptor();

    setInterval(async () => {
      const live = await faceapi
        .detectSingleFace(videoRef.current, new faceapi.TinyFaceDetectorOptions())
        .withFaceLandmarks()
        .withFaceDescriptor();

      if (!live) return;

      const distance = faceapi.euclideanDistance(reference.descriptor, live.descriptor);

      if (distance > 0.50) {
        socket.emit("suspicious", {
          sessionId,
          studentId: userId,
          type: "Unknown Person Detected"
        });
      }

    }, 2000);
  };

  checkFaceContinuously();
}, []);
