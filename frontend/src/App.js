import { useState } from "react";
import FacultyDashboard from "./components/FacultyDashboard";
import StudentView from "./components/StudentView";
import FaceAuth from "./auth/FaceAuth";
import LiveMonitoring from "./proctoring/LiveMonitoring";
import BehaviorAnalysis from "./proctoring/BehaviorAnalysis";
import SessionReports from "./proctoring/SessionReports";

import { useState } from "react";


// ...existing code...
function App() {
  const [role, setRole] = useState("");

  return (
    <div style={{ padding: "30px", fontFamily: "Arial" }}>
      <h1 style={{ fontSize: "32px" }}>Cloud Proctoring System</h1>

      {!role && (
        <>
          <p>Select your role:</p>

          <button onClick={() => setRole("faculty")}
            style={{ padding: "10px 20px", marginRight: "10px" }}>
            Faculty
          </button>

          <button onClick={() => setRole("student")}
            style={{ padding: "10px 20px" }}>
            Student
          </button>
        </>
      )}

      {role === "faculty" && (
        <>
          <button onClick={() => setRole("")} style={{ marginBottom: "10px" }}>
            Back
          </button>
          <FacultyDashboard />
          <LiveMonitoring />
          <h2>Behavior Analysis</h2>
          <BehaviorAnalysis />
          <SessionReports />
        </>
      )}

      {role === "student" && (
        <>
          <button onClick={() => setRole("")} style={{ marginBottom: "10px" }}>
            Back
          </button>
          <FaceAuth />
          <StudentView />
        </>
      )}
    </div>
  );
}

export default App;