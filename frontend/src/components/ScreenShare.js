import { useEffect } from "react";
import { io } from "socket.io-client";

const socket = io("http://localhost:5000");

export default function ScreenShare({ room }) {
  const startShare = async () => {
    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: true
    });

    const recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (event) => {
      socket.emit("screenStream", {
        room,
        stream: event.data
      });
    };

    recorder.start(200);
  };

  return (
    <div className="mt-3">
      <button className="btn btn-warning" onClick={startShare}>
        Start Screen Share
      </button>
    </div>
  );
}
