import { useState } from "react";
import API from "../api";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const loginUser = async () => {
    try {
      const res = await API.post("/auth/login", { email, password });

      localStorage.setItem("token", res.data.token);
      localStorage.setItem("role", res.data.user.role);

      if (res.data.user.role === "student") {
        window.location.href = "/student";
      } else {
        window.location.href = "/faculty";
      }
      
    } catch (err) {
      alert("Invalid credentials");
    }
  };

  return (
    <div className="container mt-5 col-4">
      <h2>Login</h2>

      <input className="form-control mt-3"
        placeholder="Email"
        onChange={(e) => setEmail(e.target.value)}
      />

      <input className="form-control mt-3"
        type="password"
        placeholder="Password"
        onChange={(e) => setPassword(e.target.value)}
      />

      <button className="btn btn-primary mt-4 w-100" onClick={loginUser}>
        Login
      </button>

      <a href="/register" className="mt-3 d-block">Create new account</a>
    </div>
  );
}
