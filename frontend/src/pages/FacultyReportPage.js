import React, { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  Divider,
} from "@mui/material";
import { getSessionSuspiciousLogs } from "../proctoring/AlertService";
import axios from "axios";

function FacultyReportPage({ sessionId }) {
  const [report, setReport] = useState(null);
  const [recordings, setRecordings] = useState([]);

  useEffect(() => {
    loadReport();
  }, []);

  const loadReport = async () => {
    const data = await getSessionSuspiciousLogs(sessionId);
    setReport(data);

    const rec = await axios.get(`${process.env.REACT_APP_API_URL}/recording/${sessionId}`);
    setRecordings(rec.data);
  };

  if (!report) return <p>Loading report...</p>;

  return (
    <div style={{ padding: 30 }}>
      <Typography variant="h4" gutterBottom>
        Proctoring Report — Session {sessionId}
      </Typography>

      <Card style={{ marginTop: 20 }}>
        <CardContent>
          <Typography variant="h6">AI-Generated Summary</Typography>
          <Typography style={{ marginTop: 10, whiteSpace: "pre-line" }}>
            {report.summary}
          </Typography>
        </CardContent>
      </Card>

      <Card style={{ marginTop: 20 }}>
        <CardContent>
          <Typography variant="h6">Suspicious Activity Timeline</Typography>

          <List>
            {report.logs.map((log, i) => (
              <React.Fragment key={i}>
                <ListItem>
                  {new Date(log.timestamp).toLocaleTimeString()} —{" "}
                  <b>{log.type}</b>
                </ListItem>
                <Divider />
              </React.Fragment>
            ))}
          </List>
        </CardContent>
      </Card>

      <Card style={{ marginTop: 20 }}>
        <CardContent>
          <Typography variant="h6">Recorded Evidence</Typography>

          {recordings.map((r) => (
            <div key={r.id} style={{ marginTop: 10 }}>
              <a href={r.url} target="_blank" rel="noopener noreferrer">
                Download Recording ({r.userId})
              </a>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

export default FacultyReportPage;
