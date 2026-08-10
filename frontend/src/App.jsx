import { useEffect, useState } from "react";
import api from "./services/api";

const Badge = ({ value }) => <span className={`badge ${String(value).toLowerCase()}`}>{value}</span>;

export default function App() {
  const [summary, setSummary] = useState();
  const [incidents, setIncidents] = useState([]);
  const [simulation, setSimulation] = useState();
  const [page, setPage] = useState("Overview");
  const [failure, setFailure] = useState("database_timeout");
  const [message, setMessage] = useState("");
  const [selected, setSelected] = useState();

  const load = async () => {
    try {
      const [dashboard, incidentRows, simulationStatus] = await Promise.all([
        api.get("/api/dashboard/summary"), api.get("/api/incidents"), api.get("/api/simulation/status"),
      ]);
      setSummary(dashboard.data); setIncidents(incidentRows.data); setSimulation(simulationStatus.data);
    } catch { setMessage("Backend unavailable"); }
  };

  useEffect(() => { load(); const id = setInterval(load, 8000); return () => clearInterval(id); }, []);
  const correlate = async () => { const result = await api.post("/api/incidents/correlate"); setMessage(`${result.data.created.length} incident(s) correlated.`); load(); };
  const start = async () => { await api.post("/api/simulation/start", { workflow: "ecommerce", failure, speed: "fast" }); setMessage("Simulation started; local collection is automatic."); load(); };

  return <main>
    <header><div><b>SignalWatch</b><small>Cloud incident intelligence</small></div><nav>{["Overview", "Incidents", "Simulation", "Knowledge Base"].map((item) => <button key={item} className={page === item ? "selected" : ""} onClick={() => setPage(item)}>{item}</button>)}</nav></header>
    {message && <p className="notice">{message}</p>}
    {page === "Overview" && <>
      <section className="hero"><div><h1>Operational clarity, not raw noise.</h1><p>Correlate structured logs into incidents and verified engineering knowledge.</p></div><button onClick={correlate}>Run correlation</button></section>
      <section className="cards">{[["Total incidents", summary?.total_incidents], ["Active", summary?.active_incidents], ["Critical", summary?.severity?.CRITICAL], ["Resolved", summary?.resolved_incidents]].map(([label, number]) => <article key={label}><small>{label}</small><strong>{number ?? "-"}</strong></article>)}</section>
      <IncidentTable rows={summary?.recent_incidents || []} select={setSelected} />
    </>}
    {page === "Incidents" && <><button onClick={correlate}>Correlate unprocessed logs</button><IncidentTable rows={incidents} select={setSelected} /></>}
    {page === "Simulation" && <section className="panel"><h1>Simulation control</h1><select value={failure} onChange={(event) => setFailure(event.target.value)}>{["database_timeout", "redis_failure", "payment_api_timeout", "auth_failure", "cpu_spike", "disk_full", "none"].map((item) => <option key={item}>{item}</option>)}</select><p>Status: <Badge value={simulation?.status || "unknown"} /></p><button onClick={start}>Start simulation</button></section>}
    {page === "Knowledge Base" && <Knowledge />}
    {selected && <Detail incident={selected} close={() => setSelected(null)} />}
  </main>;
}

function IncidentTable({ rows, select }) {
  return <div className="table"><div className="thead"><span>ID</span><span>Severity</span><span>Status</span><span>Summary</span><span>Services</span></div>{rows.map((item) => <button key={item.incident_id} className="trow" onClick={() => select(item)}><span>INC-{item.incident_id}</span><span><Badge value={item.severity} /></span><span><Badge value={item.status} /></span><span>{item.summary}</span><span>{item.affected_services?.join(", ")}</span></button>)}</div>;
}

function Detail({ incident, close }) {
  const [timeline, setTimeline] = useState([]); const [logs, setLogs] = useState([]); const [analysis, setAnalysis] = useState(); const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState({ ai_correct: true, actual_root_cause: "", actual_resolution: "", engineer_comments: "" }); const [notice, setNotice] = useState("");
  const id = incident.incident_id;
  const load = () => Promise.all([api.get(`/api/incidents/${id}/timeline`), api.get(`/api/incidents/${id}/logs`), api.get(`/api/incidents/${id}/analysis`)]).then(([timelineResult, logResult, analysisResult]) => { setTimeline(timelineResult.data); setLogs(logResult.data); setAnalysis(analysisResult.data); setLoading(false); }).catch(() => { setAnalysis({ status: "unavailable", message: "Unable to contact the backend." }); setLoading(false); });
  useEffect(() => { load(); }, [id]);
  const requestAnalysis = async () => { setLoading(true); try { setAnalysis((await api.post(`/api/incidents/${id}/analysis`)).data); } finally { setLoading(false); } };
  const submitFeedback = async (event) => { event.preventDefault(); await api.post(`/api/incidents/${id}/feedback`, feedback); setNotice("Engineer feedback saved."); };

  return <section className="panel"><div className="row"><h2>INC-{id}</h2><button className="secondary" onClick={close}>Close</button></div><p><Badge value={incident.severity} /> <Badge value={incident.status} /></p><p><b>Affected services:</b> {incident.affected_services?.join(", ")}</p>
    <h3>Observed facts — Timeline</h3>{timeline.map((item) => <p key={item.id}><b>{item.service}</b>: {item.event}</p>)}
    <h3>Observed facts — Related logs</h3>{logs.map((item) => <p key={item.id}><Badge value={item.severity} /> {item.service}: {item.message}</p>)}
    <h3>Gemini AI analysis</h3>{loading ? <p>Loading Gemini analysis…</p> : analysis?.status === "available" ? <><p><small>Model: {analysis.model}</small></p><p><b>AI inference — Summary:</b> {analysis.summary}</p><p><b>AI inference — Probable root cause:</b> {analysis.probable_root_cause}</p><p><b>Confidence:</b> {Math.round((analysis.confidence || 0) * 100)}%</p><p><b>AI inference — Suggested resolution:</b> {analysis.suggested_resolution}</p><p><b>Evidence:</b> {(analysis.evidence || []).join("; ")}</p><p><b>Alternative causes:</b> {(analysis.alternative_causes || []).join("; ")}</p><h4>Historical evidence</h4>{(analysis.historical_matches || []).map((item) => <p key={item.incident_id}>INC-{item.incident_id}: {item.root_cause} — {item.resolution}</p>)}</> : <><p>{analysis?.message || "Gemini analysis is unavailable."}</p><button onClick={requestAnalysis}>Request Gemini analysis</button>{(analysis?.historical_matches || []).map((item) => <p key={item.incident_id}>Historical evidence: INC-{item.incident_id} — {item.root_cause}</p>)}</>}
    <h3>Engineer feedback</h3><form onSubmit={submitFeedback}><label>AI diagnosis<select value={String(feedback.ai_correct)} onChange={(event) => setFeedback({ ...feedback, ai_correct: event.target.value === "true" })}><option value="true">Correct</option><option value="false">Incorrect</option></select></label><input placeholder="Actual root cause" value={feedback.actual_root_cause} onChange={(event) => setFeedback({ ...feedback, actual_root_cause: event.target.value })} /><input placeholder="Actual resolution" value={feedback.actual_resolution} onChange={(event) => setFeedback({ ...feedback, actual_resolution: event.target.value })} /><textarea placeholder="Engineer notes" value={feedback.engineer_comments} onChange={(event) => setFeedback({ ...feedback, engineer_comments: event.target.value })} /><button>Save feedback</button></form>{notice && <p>{notice}</p>}
  </section>;
}

function Knowledge() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get("/api/knowledge-base").then((result) => setRows(result.data)); }, []);
  return <>{rows.map((item) => <article key={item.id} className="panel"><b>INC-{item.incident_id}</b><p>{item.root_cause}</p><p>{item.resolution}</p></article>)}</>;
}
