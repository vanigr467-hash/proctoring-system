import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth APIs
export const authAPI = {
  login: (credentials) => api.post('/auth/login', credentials),
  register: (userData) => api.post('/auth/register', userData),
  logout: () => api.post('/auth/logout'),
  getCurrentUser: () => api.get('/auth/me')
};

// Session APIs
export const sessionAPI = {
  createSession: (data) => api.post('/sessions', data),
  getSession: (id) => api.get(`/sessions/${id}`),
  startSession: (id) => api.post(`/sessions/${id}/start`),
  endSession: (id) => api.post(`/sessions/${id}/end`),
  getFacultySessions: () => api.get('/sessions/faculty'),
  getStudentSessions: () => api.get('/sessions/student')
};

// Monitoring APIs
export const monitoringAPI = {
  verifyFace: (sessionId, imageData) => 
    api.post(`/monitoring/verify-face`, { sessionId, imageData }),
  reportActivity: (data) => api.post('/monitoring/activity', data),
  getActivityLogs: (sessionId, studentId) => 
    api.get(`/monitoring/activity/${sessionId}/${studentId}`)
};

// Report APIs
export const reportAPI = {
  getSessionReport: (sessionId) => api.get(`/reports/session/${sessionId}`),
  getStudentReport: (sessionId, studentId) => 
    api.get(`/reports/session/${sessionId}/student/${studentId}`),
  downloadRecording: (recordingId) => 
    api.get(`/reports/recording/${recordingId}`, { responseType: 'blob' })
};

export default api;
