import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Card } from "../components/ui";
import { getJSON, Job } from "../lib/api";

function formatDuration(ms?: number | null) {
  if (!ms) return "-";
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  return `${min}m ${sec % 60}s`;
}

function formatTs(ts?: number | null) {
  if (!ts) return "-";
  return new Date(ts).toLocaleString();
}

export default function Jobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [status, setStatus] = useState<string>("");
  const [agent, setAgent] = useState<string>("");

  const load = () => {
    const params = new URLSearchParams();
    params.set("limit", "100");
    if (status) params.set("status", status);
    if (agent) params.set("agent", agent);
    getJSON<Job[]>(`/api/jobs?${params.toString()}`).then(setJobs).catch(() => setJobs([]));
  };

  useEffect(() => {
    load();
  }, [status, agent]);

  const agents = useMemo(() => Array.from(new Set(jobs.map((j) => j.agent).filter(Boolean))), [jobs]);

  return (
    <Card>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="text-lg font-semibold">Jobs</div>
        <div className="flex gap-2">
          <select
            className="rounded-lg border border-base-700 bg-base-700/50 px-3 py-2 text-sm"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">All statuses</option>
            <option value="running">Running</option>
            <option value="done">Done</option>
            <option value="blocked">Blocked</option>
            <option value="error">Error</option>
          </select>
          <select
            className="rounded-lg border border-base-700 bg-base-700/50 px-3 py-2 text-sm"
            value={agent}
            onChange={(e) => setAgent(e.target.value)}
          >
            <option value="">All agents</option>
            {agents.map((name) => (
              <option key={name as string} value={name as string}>
                {name}
              </option>
            ))}
          </select>
          <button
            className="rounded-lg border border-base-700 bg-base-700/40 px-3 py-2 text-sm"
            onClick={load}
          >
            Refresh
          </button>
        </div>
      </div>
      <div className="overflow-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-slate-400">
              <th className="py-2">Job ID</th>
              <th className="py-2">Agent</th>
              <th className="py-2">Status</th>
              <th className="py-2">Started</th>
              <th className="py-2">Duration</th>
              <th className="py-2">Model</th>
              <th className="py-2">Prompt</th>
              <th className="py-2">Completion</th>
              <th className="py-2">Total</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.job_id} className="border-t border-base-700/60">
                <td className="py-2">
                  <Link className="text-accent-cyan hover:underline" to={`/jobs/${job.job_id}`}>
                    {job.job_id.slice(0, 8)}
                  </Link>
                </td>
                <td className="py-2">{job.agent ?? "-"}</td>
                <td className="py-2">
                  <Badge
                    text={job.status ?? "unknown"}
                    tone={job.status === "running" ? "cyan" : job.status === "blocked" ? "amber" : job.status === "error" ? "pink" : "slate"}
                  />
                </td>
                <td className="py-2">{formatTs(job.started_ts)}</td>
                <td className="py-2">{formatDuration(job.duration_ms)}</td>
                <td className="py-2">{job.model ?? "-"}</td>
                <td className="py-2">{job.prompt_tokens_exact ?? job.prompt_tokens_est ?? 0}</td>
                <td className="py-2">{job.completion_tokens_exact ?? job.completion_tokens_est ?? 0}</td>
                <td className="py-2">{job.total_tokens_exact ?? job.total_tokens_est ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
