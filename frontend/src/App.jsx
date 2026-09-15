import {useEffect, useState} from "react";

function App() {
  const [backendStatus, setBackendStatus] = useState("Checking...");

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/health")
      .then(response => response.json())
      .then(data => {
        setBackendStatus(data.status);
      })
      .catch(() => {
        setBackendStatus("Backend unavailable");
      });
  }, []);

  return (
    <main>
      <h1>Electoral Analytics Explorer</h1>

      <p>How does money influence U.S. elections?</p>

      <p>
        Backend status: <strong>{backendStatus}</strong>
      </p>
    </main>
  );
}

export default App;
