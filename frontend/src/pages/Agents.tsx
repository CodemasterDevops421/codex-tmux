import { useEffect, useMemo, useState } from "react";
import { Card, Badge } from "../components/ui";
import { getJSON, Agent, Event } from "../lib/api";

export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [doctor, setDoctor] = useState<any>(null);

  useEffect(() => {
    getJSON<Agent[]>("/api/agents").then(setAgents).catch(() => setAgents([]));
    getJSON<Event[]>("/api/events?limit=200").then(setEvents).catch(() => setEvents([]));
    getJSON<{ agents: any }>("/api/doctor").then(setDoctor).catch(() => setDoctor(null));
  }, []);

  const grouped = useMemo(() => {
    const map: Record<string, Event[]> = {};
    for (const ev of events) {
      const agent = ev.agent || "unknown";
      if (!map[agent]) map[agent] = [];
      map[agent].push(ev);
    }
    return map;
  }, [events]);

  return (
    <div className="space-y-6">
      {doctor ? (
        <Card>
          <div className="mb-3 text-sm uppercase tracking-widest text-slate-400">Doctor</div>
          <div className="grid gap-3 md:grid-cols-2">
            {Object.entries(doctor.agents || {}).map(([agent, info]: any) => (
              <div key={agent} className="rounded-xl border border-base-700 bg-base-700/30 p-3">
                <div className="flex items-center justify-between">
                  <div className="font-semibold">{agent}</div>
                  <Badge text={info.responsive ? "responsive" : "stale"} tone={info.responsive ? "lime" : "amber"} />
                </div>
                <div className="mt-2 text-xs text-slate-400">Pane: {info.pane_id ?? "-"}</div>
                <div className="text-xs text-slate-400">Mode: {info.mode ?? "unknown"}</div>
                <div className="text-xs text-slate-400">Auth needed: {info.auth_needed ? "yes" : "no"}</div>
              </div>
            ))}
          </div>
        </Card>
      ) : null}
      <div className="grid gap-4 md:grid-cols-2">
        {agents.map((agent) => (
          <Card key={agent.agent}>
            <div className="mb-3 flex items-center justify-between">
              <div className="text-lg font-semibold">{agent.agent}</div>
              <Badge
                text={agent.status ?? "idle"}
                tone={agent.status === "running" ? "cyan" : agent.status === "blocked" ? "amber" : agent.status === "error" ? "pink" : "slate"}
              />
            </div>
            <div className="h-64 overflow-auto rounded-xl border border-base-700 bg-base-700/30 p-3 text-sm">
              {(grouped[agent.agent] || []).slice(0, 100).map((ev, idx) => (
                <div key={`${ev.ts}-${idx}`} className="mb-2">
                  <div className="text-xs text-slate-500">{new Date(ev.ts).toLocaleTimeString()}</div>
                  <div className="text-slate-200">{ev.text || ev.prompt_text || ev.job_id}</div>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
