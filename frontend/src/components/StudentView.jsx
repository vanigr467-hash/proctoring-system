import React, { useEffect, useRef, useState } from 'react';
import Webcam from 'react-webcam';
import io from 'socket.io-client';
import { toast } from 'react-toastify';
import { Box, Paper, Typography, Button, Alert } from '@mui/material';
import { monitoringAPI } from '../services/api';

const SOCKET_URL = process.env.REACT_APP_SOCKET_URL || 'http://localhost:5000';

const StudentView = ({ session, user }) => {
  const webcamRef = useRef(null);
  const screenStreamRef = useRef(null);
  const socketRef = useRef(null);
  const [isVerified, setIsVerified] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    // Initialize socket connection
    socketRef.current = io(SOCKET_URL);

    socketRef.current.on('connect', () => {
      console.log('Connected to server');
      socketRef.current.emit('join-session', {
        sessionId: session.id,
        userId: user.id,
        role: 'student'
      });
    });

    socketRef.current.on('alert', (data) => {
      setAlerts(prev => [...prev, data]);
      toast.warning(`Alert: ${data.activity.description}`);
    });

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
      stopScreenShare();
    };
  }, [session.id, user.id]);

  const verifyFace = async () => {
    try {
      const imageSrc = webcamRef.current.getScreenshot();
      const response = await monitoringAPI.verifyFace(session.id, imageSrc);
      
      if (response.data.verified) {
        setIsVerified(true);
        toast.success('Face verified successfully!');
        startVideoStream();
      } else {
        toast.error('Face verification failed. Please try again.');
      }
    } catch (error) {
      toast.error('Error during face verification');
      console.error(error);
    }
  };

  const startVideoStream = () => {
    setIsRecording(true);
    const stream = webcamRef.current.stream;
    
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: 'video/webm;codecs=vp8,opus'
    });

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        const reader = new FileReader();
        reader.readAsArrayBuffer(event.data);
        reader.onloadend = () => {
          socketRef.current.emit('video-stream', {
            sessionId: session.id,
            userId: user.id,
            chunk: reader.result
          });
        };
      }
    };

    mediaRecorder.start(1000); // Send chunks every second

    // Face detection interval
    const faceDetectionInterval = setInterval(async () => {
      const imageSrc = webcamRef.current.getScreenshot();
      // Analyze face position, count, etc.
      detectAnomalies(imageSrc);
    }, 3000);

    return () => {
      mediaRecorder.stop();
      clearInterval(faceDetectionInterval);
    };
  };

  const detectAnomalies = async (imageSrc) => {
    // This would call a backend service for AI-based detection
    // Simplified for demonstration
    try {
      // Check for multiple faces, looking away, etc.
      const canvas = document.createElement('canvas');
      const img = new Image();
      img.src = imageSrc;
      
      // Would use face detection library or API here
      // For now, this is a placeholder
    } catch (error) {
      console.error('Error detecting anomalies:', error);
    }
  };

  const startScreenShare = async () => {
    try {
      const screenStream = await navigator.mediaDevices.getDisplayMedia({
        video: { mediaSource: 'screen' }
      });
      
      screenStreamRef.current = screenStream;

      const mediaRecorder = new MediaRecorder(screenStream);
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          const reader = new FileReader();
          reader.readAsArrayBuffer(event.data);
          reader.onloadend = () => {
            socketRef.current.emit('screen-share', {
              sessionId: session.id,
              userId: user.id,
              screenData: reader.result
            });
          };
        }
      };

      mediaRecorder.start(2000);

      screenStream.getVideoTracks()[0].onended = () => {
        socketRef.current.emit('suspicious-activity', {
          sessionId: session.id,
          userId: user.id,
          activity: {
            type: 'screen_share_stopped',
            severity: 'high',
            description: 'Student stopped screen sharing'
          }
        });
      };

      toast.info('Screen sharing started');
    } catch (error) {
      toast.error('Failed to start screen sharing');
      console.error(error);
    }
  };

  const stopScreenShare = () => {
    if (screenStreamRef.current) {
      screenStreamRef.current.getTracks().forEach(track => track.stop());
      screenStreamRef.current = null;
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h5" gutterBottom>
          {session.title}
        </Typography>
        <Typography variant="body1" color="text.secondary">
          {session.description}
        </Typography>
      </Paper>

      {!isVerified ? (
        <Paper elevation={3} sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom>
            Face Verification Required
          </Typography>
          <Box sx={{ my: 3 }}>
            <Webcam
              ref={webcamRef}
              audio={false}
              screenshotFormat="image/jpeg"
              videoConstraints={{
                width: 640,
                height: 480,
                facingMode: 'user'
              }}
              style={{ width: '100%', maxWidth: '640px', borderRadius: '8px' }}
            />
          </Box>
          <Button
            variant="contained"
            color="primary"
            size="large"
            onClick={verifyFace}
          >
            Verify Face
          </Button>
        </Paper>
      ) : (
        <>
          <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Live Monitoring
            </Typography>
            <Box sx={{ my: 2 }}>
              <Webcam
                ref={webcamRef}
                audio={true}
                screenshotFormat="image/jpeg"
                videoConstraints={{
                  width: 640,
                  height: 480,
                  facingMode: 'user'
                }}
                style={{ width: '100%', maxWidth: '640px', borderRadius: '8px' }}
              />
            </Box>
            <Button
              variant="contained"
              color="secondary"
              onClick={startScreenShare}
              sx={{ mr: 2 }}
            >
              Start Screen Share
            </Button>
            <Button
              variant="outlined"
              color="error"
              onClick={stopScreenShare}
            >
              Stop Screen Share
            </Button>
          </Paper>

          {alerts.length > 0 && (
            <Paper elevation={3} sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Alerts
              </Typography>
              {alerts.slice(-5).map((alert, index) => (
                <Alert severity="warning" key={index} sx={{ mb: 1 }}>
                  {alert.activity.description}
                </Alert>
              ))}
            </Paper>
          )}
        </>
      )}
    </Box>
  );
};

export default StudentView;
