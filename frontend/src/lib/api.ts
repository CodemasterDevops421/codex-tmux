export type Agent = {
  agent: string;
  status: string | null;
  last_seen: number | null;
  pane_id: string | null;
  window_name: string | null;
  session: string | null;
  model: string | null;
};

export type Job = {
  job_id: string;
  agent: string | null;
  status: string | null;
  started_ts: number | null;
  updated_ts: number | null;
  duration_ms: number | null;
  prompt_text: string | null;
  prompt_hash: string | null;
  prompt_bytes: number | null;
  output_path: string | null;
  output_bytes: number | null;
  model: string | null;
  prompt_tokens_exact: number | null;
  completion_tokens_exact: number | null;
  total_tokens_exact: number | null;
  prompt_tokens_est: number | null;
  completion_tokens_est: number | null;
  total_tokens_est: number | null;
};

export type Event = {
  id?: number;
  ts: number;
  type: string;
  session?: string | null;
  agent?: string | null;
  pane_id?: string | null;
  window_name?: string | null;
  job_id?: string | null;
  payload?: string;
  text?: string;
  prompt_text?: string | null;
  prompt_hash?: string | null;
  prompt_bytes?: number | null;
  output_path?: string | null;
  output_bytes?: number | null;
  model?: string | null;
  prompt_tokens_exact?: number | null;
  completion_tokens_exact?: number | null;
  total_tokens_exact?: number | null;
  prompt_tokens_est?: number | null;
  completion_tokens_est?: number | null;
  total_tokens_est?: number | null;
  status?: string | null;
  sub_agent?: string | null;
};

export async function getJSON<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return (await res.json()) as T;
}
