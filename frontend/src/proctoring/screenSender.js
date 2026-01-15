import { socket } from "./socket";

export default async function startScreenShare(sessionId, userId) {
  try {
    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: true
    });

    const recorder = new MediaRecorder(stream, {
      mimeType: "video/webm; codecs=vp8"
    });

    recorder.ondataavailable = (e) => {
      socket.emit("screen-share", {
        sessionId,
        userId,
        screen: e.data
      });
    };

    recorder.start(500);
  } catch (err) {
    console.error("Screen share error:", err);
  }
}
