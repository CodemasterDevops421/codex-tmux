import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Badge, Button, Card, Stat } from "../components/ui";
import { getJSON, Job, Event } from "../lib/api";

export default function JobDetail() {
  const { jobId } = useParams();
  const [job, setJob] = useState<Job | null>(null);
  const [events, setEvents] = useState<Event[]>([]);

  useEffect(() => {
    if (!jobId) return;
    getJSON<{ job: Job; events: Event[] }>(`/api/jobs/${jobId}`).then((data) => {
      setJob(data.job);
      setEvents(data.events);
    });
  }, [jobId]);

  const transcript = useMemo(() => {
    return events
      .filter((ev) => ev.text)
      .map((ev) => ev.text)
      .join("\n");
  }, [events]);

  const subAgents = useMemo(() => {
    const set = new Set<string>();
    for (const ev of events) {
      if (ev.sub_agent) set.add(ev.sub_agent);
    }
    return Array.from(set);
  }, [events]);

  const download = () => {
    const blob = new Blob([transcript], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${jobId}-transcript.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!job) {
    return <Card>Loading...</Card>;
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="text-lg font-semibold">Job {job.job_id.slice(0, 8)}</div>
          <Badge
            text={job.status ?? "unknown"}
            tone={job.status === "running" ? "cyan" : job.status === "blocked" ? "amber" : job.status === "error" ? "pink" : "slate"}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Stat label="Agent" value={job.agent ?? "-"} />
          <Stat label="Model" value={job.model ?? "-"} />
          <Stat label="Prompt Tokens" value={job.prompt_tokens_exact ?? job.prompt_tokens_est ?? 0} />
          <Stat label="Completion Tokens" value={job.completion_tokens_exact ?? job.completion_tokens_est ?? 0} />
        </div>
        <div>
          <div className="mb-2 text-xs uppercase tracking-widest text-slate-400">Prompt</div>
          <pre className="max-h-64 overflow-auto rounded-xl border border-base-700 bg-base-700/40 p-3 text-sm text-slate-100">
            {job.prompt_text ?? job.prompt_hash ?? "(not captured)"}
          </pre>
        </div>
        {subAgents.length ? (
          <div>
            <div className="mb-2 text-xs uppercase tracking-widest text-slate-400">Sub-agents</div>
            <div className="flex flex-wrap gap-2">
              {subAgents.map((name) => (
                <Badge key={name} text={name} tone="violet" />
              ))}
            </div>
          </div>
        ) : null}
      </Card>
      <Card className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="text-xs uppercase tracking-widest text-slate-400">Transcript</div>
          <Button onClick={download}>Download transcript</Button>
        </div>
        <pre className="h-[520px] overflow-auto rounded-xl border border-base-700 bg-base-700/30 p-3 text-sm text-slate-100">
          {transcript || "No transcript yet."}
        </pre>
      </Card>
    </div>
  );
}
