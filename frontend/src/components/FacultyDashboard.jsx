import React, { useEffect, useState, useRef } from 'react';
import io from 'socket.io-client';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  Chip,
  Button,
  List,
  ListItem,
  ListItemText,
  Avatar
} from '@mui/material';
import { WarningAmber, CheckCircle, Error } from '@mui/icons-material';
import { toast } from 'react-toastify';

const SOCKET_URL = process.env.REACT_APP_SOCKET_URL || 'http://localhost:5000';

const FacultyDashboard = ({ session, user }) => {
  const [students, setStudents] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const socketRef = useRef(null);
  const videoRefs = useRef({});

  useEffect(() => {
    socketRef.current = io(SOCKET_URL);

    socketRef.current.on('connect', () => {
      console.log('Faculty connected to server');
      socketRef.current.emit('join-session', {
        sessionId: session.id,
        userId: user.id,
        role: 'faculty'
      });
    });

    socketRef.current.on('student-video-stream', (data) => {
      const { userId, chunk } = data;
      
      if (videoRefs.current[userId]) {
        const blob = new Blob([chunk], { type: 'video/webm' });
        const url = URL.createObjectURL(blob);
        videoRefs.current[userId].src = url;
      }
    });

    socketRef.current.on('student-screen', (data) => {
      // Handle screen share display
      console.log('Screen share received from:', data.userId);
    });

    socketRef.current.on('alert', (data) => {
      setAlerts(prev => [data, ...prev].slice(0, 50)); // Keep last 50 alerts
      toast.warning(`Alert from student: ${data.activity.description}`);
    });

    // Load session participants
    loadParticipants();

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, [session.id, user.id]);

  const loadParticipants = async () => {
    // Fetch participants from API
    // This is simplified
    setStudents(session.participants || []);
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'info';
      case 'low': return 'success';
      default: return 'default';
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return <Error color="error" />;
      case 'medium':
        return <WarningAmber color="warning" />;
      default:
        return <CheckCircle color="success" />;
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Faculty Monitoring Dashboard
        </Typography>
        <Typography variant="h6" color="text.secondary">
          {session.title}
        </Typography>
        <Chip
          label={session.status}
          color={session.status === 'ongoing' ? 'success' : 'default'}
          sx={{ mt: 1 }}
        />
      </Paper>

      <Grid container spacing={3}>
        {/* Student Video Grid */}
        <Grid item xs={12} md={8}>
          <Paper elevation={3} sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Live Student Feeds ({students.length})
            </Typography>
            <Grid container spacing={2}>
              {students.map((student) => (
                <Grid item xs={12} sm={6} md={4} key={student.id}>
                  <Card
                    sx={{
                      cursor: 'pointer',
                      border: selectedStudent?.id === student.id ? '2px solid #1976d2' : 'none'
                    }}
                    onClick={() => setSelectedStudent(student)}
                  >
                    <video
                      ref={(el) => (videoRefs.current[student.id] = el)}
                      autoPlay
                      muted
                      style={{
                        width: '100%',
                        height: '180px',
                        objectFit: 'cover',
                        backgroundColor: '#000'
                      }}
                    />
                    <CardContent>
                      <Typography variant="subtitle2">
                        {student.firstName} {student.lastName}
                      </Typography>
                      <Chip
                        size="small"
                        label={student.faceVerified ? 'Verified' : 'Not Verified'}
                        color={student.faceVerified ? 'success' : 'error'}
                        sx={{ mt: 1 }}
                      />
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Paper>
        </Grid>

        {/* Alerts Panel */}
        <Grid item xs={12} md={4}>
          <Paper elevation={3} sx={{ p: 2, height: '600px', overflow: 'auto' }}>
            <Typography variant="h6" gutterBottom>
              Activity Alerts
            </Typography>
            <List>
              {alerts.map((alert, index) => (
                <ListItem
                  key={index}
                  sx={{
                    bgcolor: 'background.paper',
                    mb: 1,
                    borderRadius: 1,
                    border: '1px solid #e0e0e0'
                  }}
                >
                  <Avatar sx={{ mr: 2 }}>
                    {getSeverityIcon(alert.severity)}
                  </Avatar>
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="body2">
                          Student {alert.userId}
                        </Typography>
                        <Chip
                          size="small"
                          label={alert.severity}
                          color={getSeverityColor(alert.severity)}
                        />
                      </Box>
                    }
                    secondary={
                      <>
                        <Typography variant="body2" color="text.secondary">
                          {alert.activity.description}
                        </Typography>
                        <Typography variant="caption" color="text.disabled">
                          {new Date(alert.timestamp).toLocaleTimeString()}
                        </Typography>
                      </>
                    }
                  />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>

        {/* Selected Student Details */}
        {selectedStudent && (
          <Grid item xs={12}>
            <Paper elevation={3} sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Student Details: {selectedStudent.firstName} {selectedStudent.lastName}
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="body2">
                    <strong>Email:</strong> {selectedStudent.email}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Verification Score:</strong>{' '}
                    {selectedStudent.faceVerificationScore || 'N/A'}%
                  </Typography>
                  <Typography variant="body2">
                    <strong>Status:</strong> {selectedStudent.status}
                  </Typography>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Button
                    variant="contained"
                    color="primary"
                    sx={{ mr: 1 }}
                  >
                    View Full Screen
                  </Button>
                  <Button
                    variant="outlined"
                    color="secondary"
                  >
                    View Activity Log
                  </Button>
                </Grid>
              </Grid>
            </Paper>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default FacultyDashboard;
