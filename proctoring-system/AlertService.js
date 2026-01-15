import axios from "axios";

const API = process.env.REACT_APP_API_URL;

export const getSessionSuspiciousLogs = async (sessionId) => {
  if (!API) {
    throw new Error("REACT_APP_API_URL environment variable is not set");
  }
  
  if (!sessionId) {
    throw new Error("sessionId is required");
  }

  try {
    const res = await axios.get(`${API}/api/suspicious/${sessionId}`);
    return res.data;
  } catch (error) {
    console.error("Error fetching suspicious logs:", error.message);
    throw error;
  }
};