import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Bar, BarChart } from "recharts";
import { Card, Badge, Stat } from "../components/ui";
import { getJSON, Agent, Job, Event } from "../lib/api";
import { useEventStream } from "../lib/ws";

function formatTs(ts?: number | null) {
  if (!ts) return "-";
  return new Date(ts).toLocaleTimeString();
}

export default function Dashboard() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const { events: wsEvents } = useEventStream();

  useEffect(() => {
    getJSON<Agent[]>("/api/agents").then(setAgents).catch(() => setAgents([]));
    getJSON<Job[]>("/api/jobs?limit=20").then(setJobs).catch(() => setJobs([]));
    getJSON<Event[]>("/api/events?limit=30").then(setEvents).catch(() => setEvents([]));
  }, []);

  useEffect(() => {
    if (wsEvents.length === 0) return;
    setEvents((prev) => [wsEvents[0], ...prev].slice(0, 50));
  }, [wsEvents]);

  const tokensByAgent = useMemo(() => {
    const map: Record<string, { agent: string; prompt: number; completion: number }> = {};
    for (const job of jobs) {
      const name = job.agent || "unknown";
      if (!map[name]) map[name] = { agent: name, prompt: 0, completion: 0 };
      map[name].prompt += job.prompt_tokens_exact ?? job.prompt_tokens_est ?? 0;
      map[name].completion += job.completion_tokens_exact ?? job.completion_tokens_est ?? 0;
    }
    return Object.values(map);
  }, [jobs]);

  const tokensOverTime = useMemo(() => {
    const points = events
      .filter((ev) => ev.type && ev.ts)
      .slice(0, 40)
      .map((ev) => ({
        ts: new Date(ev.ts).toLocaleTimeString(),
        tokens: (ev.total_tokens_exact ?? ev.total_tokens_est) ?? 0
      }))
      .reverse();
    return points;
  }, [events]);

  return (
    <div className="space-y-8">
      <section className="grid gap-4 md:grid-cols-4">
        {agents.map((agent) => (
          <Card key={agent.agent}>
            <div className="flex items-center justify-between">
              <div className="text-lg font-semibold">{agent.agent}</div>
              <Badge
                text={agent.status ?? "idle"}
                tone={agent.status === "running" ? "cyan" : agent.status === "blocked" ? "amber" : agent.status === "error" ? "pink" : "slate"}
              />
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <Stat label="Last Seen" value={formatTs(agent.last_seen)} />
              <Stat label="Pane" value={agent.pane_id ?? "-"} />
            </div>
            <div className="mt-3 text-xs text-slate-400">Model: {agent.model ?? "unknown"}</div>
          </Card>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <div className="mb-4 text-sm uppercase tracking-widest text-slate-400">Controller timeline</div>
          <div className="space-y-3 max-h-64 overflow-auto pr-2">
            {events.map((event, idx) => (
              <div key={`${event.ts}-${idx}`} className="rounded-xl border border-base-700/80 bg-base-700/30 p-3">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <div>{new Date(event.ts).toLocaleTimeString()}</div>
                  <div>{event.type}</div>
                </div>
                <div className="mt-1 text-sm text-slate-200">
                  {event.text || event.prompt_text || event.job_id || "event"}
                </div>
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <div className="mb-4 text-sm uppercase tracking-widest text-slate-400">Token usage by agent</div>
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={tokensByAgent}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2a44" />
                <XAxis dataKey="agent" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1f2a44" }} />
                <Bar dataKey="prompt" stackId="a" fill="#37e4ff" />
                <Bar dataKey="completion" stackId="a" fill="#ff5c8a" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </section>

      <section>
        <Card>
          <div className="mb-4 text-sm uppercase tracking-widest text-slate-400">Tokens over time</div>
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={tokensOverTime}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2a44" />
                <XAxis dataKey="ts" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1f2a44" }} />
                <Line type="monotone" dataKey="tokens" stroke="#9dff75" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </section>
    </div>
  );
}
