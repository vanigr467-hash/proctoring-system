import { socket } from "./socket";

export default async function startVideoStream(videoRef, sessionId, userId) {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: true
    });

    videoRef.current.srcObject = stream;

    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: "video/webm; codecs=vp8"
    });

    mediaRecorder.ondataavailable = (e) => {
      socket.emit("student-video", {
        sessionId,
        userId,
        chunk: e.data
      });
    };

    mediaRecorder.start(500); // send chunks every 0.5 sec
  } catch (err) {
    alert("Camera/Mic Permission Denied");
    console.error(err);
  }
}
