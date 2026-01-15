const socketIO = require("socket.io");

let io;

module.exports.initializeSocket = (server) => {
  io = socketIO(server, {
    cors: {
      origin: "*",
      methods: ["GET", "POST"]
    },
    maxHttpBufferSize: 1e7 // 10MB frame limit
  });

  io.on("connection", (socket) => {
    console.log("Client connected:", socket.id);

    // Student joins session room
    socket.on("join-session", ({ sessionId, userId, role }) => {
      socket.join(sessionId);

      console.log(`${role} ${userId} joined session: ${sessionId}`);

      io.to(sessionId).emit("user-joined", { userId, role });
    });

    // Receive student video frame
    socket.on("video-frame", (data) => {
      const { sessionId, studentId, frame } = data;

      // broadcast to faculty only
      socket.to(sessionId).emit("receive-frame", {
        studentId,
        frame,
        timestamp: Date.now()
      });
    });

    // Suspicious detection event
    socket.on("suspicious", (event) => {
      const { sessionId, studentId, type } = event;

      io.to(sessionId).emit("alert", {
        studentId,
        type,
        time: Date.now()
      });
    });

    socket.on("disconnect", () => {
      console.log("Client disconnected:", socket.id);
    });
  });

  return io;
};

module.exports.getIO = () => io;

module.exports = (io) => {
  io.on("connection", (socket) => {
    console.log("User connected:", socket.id);

    socket.on("student-video", (data) => {
      socket.broadcast.emit("faculty-view", data);
    });

    socket.on("disconnect", () => {
      console.log("Disconnected:", socket.id);
    });
  });
};
