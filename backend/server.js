// ...existing code...
require("dotenv").config();
const express = require("express");
const http = require("http");
const socketio = require("socket.io");
const cors = require("cors");
const helmet = require("helmet");
const axios = require("axios");
const rateLimit = require("express-rate-limit");

let connectDB;
try {
  connectDB = require("./config/db").connectDB;
} catch (e) {
  try {
    connectDB = require("./config/database").connectDB;
  } catch (err) {
    connectDB = null;
  }
}

const authRoutes = require("./routes/authRoutes");
let sessionRoutes, recordingRoutes, suspiciousRoutes, liveSessionRoutes;
try {
  sessionRoutes = require("./routes/sessionRoutes");
} catch (e) {
  sessionRoutes = require("./src/routes/sessionRoutes");
}
try {
  recordingRoutes = require("./src/routes/recordingRoutes");
} catch (e) {
  recordingRoutes = null;
}
try {
  suspiciousRoutes = require("./src/routes/suspiciousRoutes");
} catch (e) {
  suspiciousRoutes = null;
}
try {
  liveSessionRoutes = require("./src/routes/liveSessionRoutes");
} catch (e) {
  liveSessionRoutes = null;
}

let logger;
try {
  logger = require("./src/utils/logger");
} catch (e) {
  logger = console;
}

// optional model import if available
let ActivityLog;
try {
  ({ ActivityLog } = require("./src/models"));
} catch (e) {
  ActivityLog = null;
}

const app = express();
const server = http.createServer(app);

const io = socketio(server, {
  cors: { origin: process.env.FRONTEND_URL || "*" }
});

// Middlewares
app.use(cors({ origin: process.env.FRONTEND_URL || "*" }));
app.use(helmet());
app.use(express.json());

// basic rate limiter on /api/*
const limiter = rateLimit({
  windowMs: 60 * 1000,
  max: 120,
});
app.use("/api/", limiter);

// Routes
app.use("/api/auth", authRoutes);
if (sessionRoutes) app.use("/api/session", sessionRoutes);
if (recordingRoutes) app.use("/api/recording", recordingRoutes);
if (suspiciousRoutes) app.use("/api/suspicious", suspiciousRoutes);
if (liveSessionRoutes) app.use("/api/live", liveSessionRoutes);

app.get("/", (req, res) => res.send("Proctoring Backend Running"));

// WebSocket handlers (rooms: session-<id>, student-<id>, faculty-<id>)
io.on("connection", (socket) => {
  logger.info?.(`Client connected: ${socket.id}`);

  socket.on("join-session", ({ sessionId, userId, role }) => {
    if (!sessionId || !userId) return;
    socket.join(`session-${sessionId}`);
    socket.join(`${role}-${userId}`);
    io.to(`session-${sessionId}`).emit("participant-update", {
      userId,
      role,
      status: "online",
      timestamp: new Date(),
    });
  });

  // backward-compatible event name
  socket.on("join-room", (payload) => socket.emit("join-session", payload));

  const handleVideo = ({ sessionId, userId, chunk }) => {
    if (!sessionId || !userId) return;
    socket.to(`session-${sessionId}`).emit("render-video", {
      userId,
      chunk,
      timestamp: Date.now(),
    });
  };
  socket.on("video-stream", handleVideo);
  socket.on("student-video", handleVideo);

  socket.on("screen-share", ({ sessionId, userId, screen }) => {
    if (!sessionId || !userId) return;
    socket.to(`session-${sessionId}`).emit("render-screen", {
      userId,
      screen,
      timestamp: Date.now(),
    });
  });

  socket.on("suspicious-activity", async (data) => {
    const { userId, sessionId, type } = data || {};
    if (!sessionId) return;

    // notify faculty in session
    io.to(`session-${sessionId}`).emit("faculty-alert", data);

    // persist via API if configured
    try {
      if (process.env.API_URL) {
        await axios.post(`${process.env.API_URL}/suspicious/add`, {
          userId,
          sessionId,
          type,
          timestamp: new Date(),
        });
      }
    } catch (err) {
      logger.error?.("Failed to POST suspicious activity to API_URL:", err.message);
    }

    // persist locally if model available
    try {
      if (ActivityLog) {
        await ActivityLog.create({
          sessionId,
          userId,
          type,
          timestamp: new Date(),
        });
      }
    } catch (err) {
      logger.error?.("Failed to save ActivityLog:", err.message);
    }
  });

  // backward-compatible name
  socket.on("suspicious", (data) => socket.emit("suspicious-activity", data));

  socket.on("disconnect", () => {
    io.emit("participant-update", {
      status: "offline",
      userId: socket.id,
      timestamp: new Date(),
    });
  });
});

// Start server
const start = async () => {
  if (connectDB) {
    try {
      await connectDB();
      logger.info?.("Database connected");
    } catch (err) {
      logger.error?.("Database connection failed:", err);
      process.exit(1);
    }
  } else {
    logger.warn?.("No connectDB found; skipping DB connection");
  }

  const PORT = process.env.PORT || 5000;
  server.listen(PORT, () => {
    logger.info?.(`🚀 Backend running on port ${PORT}`);
  });
};

start();
// ...existing code...