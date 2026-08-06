import { useEffect, useState } from "react";

import api from "./services/api";

function App() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api
      .get("/api/health")
      .then((res) => setHealth(res.data))
      .catch(() => setError(true));
  }, []);

  const connected = health?.status === "ok";

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center">
      <div className="bg-white shadow-md rounded-lg p-8 w-full max-w-md text-center">
        <h1 className="text-xl font-semibold text-slate-800 mb-4">
          Cloud-Based Log Aggregation & Alerting System
        </h1>

        <div className="flex items-center justify-center gap-2 mb-2">
          <span
            className={`h-3 w-3 rounded-full ${
              connected ? "bg-green-500" : error ? "bg-red-500" : "bg-yellow-400"
            }`}
          />
          <span className="text-slate-600">
            {connected
              ? "Backend Connected"
              : error
                ? "Backend Unreachable"
                : "Checking backend..."}
          </span>
        </div>

        {health && (
          <p className="text-sm text-slate-400">
            Database: {health.database}
          </p>
        )}
      </div>
    </div>
  );
}

export default App;
