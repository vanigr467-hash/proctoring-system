import React from "react";
import { Card, CardContent, Typography } from "@mui/material";

function StudentTile({ user, videoRef, screenRef, alerts }) {
  return (
    <Card style={{ width: 300, margin: 10 }}>
      <CardContent>
        <Typography variant="h6">{user.name || user.userId}</Typography>

        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          style={{ width: "100%", borderRadius: 8, marginTop: 10 }}
        ></video>

        {screenRef && (
          <video
            ref={screenRef}
            autoPlay
            muted
            playsInline
            style={{ width: "100%", borderRadius: 8, marginTop: 10 }}
          ></video>
        )}

        <div style={{ marginTop: 10 }}>
          <Typography variant="body2">
            Alerts: {alerts.length}
          </Typography>
        </div>
      </CardContent>
    </Card>
  );
}

export default StudentTile;
