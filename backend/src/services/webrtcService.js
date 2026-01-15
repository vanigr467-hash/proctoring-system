// Simple placeholder WebRTC service to avoid server crash

function initializeWebRTC(io) {
  console.log("WebRTC service initialized (placeholder)");
  
  io.on("connection", (socket) => {
    socket.on("offer", (data) => {
      socket.to(data.target).emit("offer", data);
    });

    socket.on("answer", (data) => {
      socket.to(data.target).emit("answer", data);
    });

    socket.on("ice-candidate", (data) => {
      socket.to(data.target).emit("ice-candidate", data);
    });
  });
}

module.exports = { initializeWebRTC };
