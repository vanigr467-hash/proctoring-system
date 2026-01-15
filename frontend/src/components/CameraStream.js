import { useEffect, useRef } from "react";
import { io } from "socket.io-client";

const socket = io("http://localhost:5000");

export default function CameraStream({ room }) {
  const videoRef = useRef();

  useEffect(() => {
    socket.emit("joinRoom", room);

    navigator.mediaDevices.getUserMedia({ video: true }).then((stream) => {
      videoRef.current.srcObject = stream;

      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (event) => {
        socket.emit("cameraStream", {
          room,
          stream: event.data
        });
      };

      recorder.start(200);
    });
  }, []);

  return (
    <div>
      <h4>Camera Feed</h4>
      <video ref={videoRef} autoPlay width="300" />
    </div>
  );
}
