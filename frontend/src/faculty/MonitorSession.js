import React, { useEffect, useState } from "react";
import io from "socket.io-client";

const socket = io(process.env.REACT_APP_SOCKET_URL);

function MonitorSession({ sessionId }) {
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    socket.emit("join", sessionId);

    socket.on("alert", (event) => {
      setAlerts((prev) => [...prev, event]);
    });
  }, []);

  return (
    <div>
      <h2>Live Alerts</h2>
      <ul>
        {alerts.map((a, i) => (
          <li key={i}>
            <strong>{a.userId}</strong>: {a.type} – {new Date(a.timestamp).toLocaleTimeString()}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default MonitorSession;
