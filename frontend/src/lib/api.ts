const API_BASE = "/api";

export interface SourceRef {
  doc_id: string;
  file_name: string;
  source_type: string;
  chunk_text: string;
  score: number;
  vault_path?: string;
  heading_path?: string;
  url?: string;
}

export interface ChatResponse {
  answer: string;
  sources: SourceRef[];
  session_id: string;
}

export interface IndexStats {
  total_documents: number;
  total_chunks: number;
  source_breakdown: Record<string, number>;
}

export interface SyncStatus {
  total_files: number;
  indexed_files: number;
  new_files: number;
  updated_files: number;
  removed_files: number;
  is_syncing: boolean;
}

export async function chat(question: string, sessionId?: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
  return res.json();
}

export async function chatStream(
  question: string,
  sessionId: string | undefined,
  onSources: (sources: SourceRef[], sessionId: string) => void,
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (err: Error) => void
) {
  try {
    const res = await fetch(`${API_BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, session_id: sessionId }),
    });

    if (!res.ok || !res.body) {
      throw new Error(`Stream failed: ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const data = JSON.parse(line.slice(6));

        if (data.type === "sources") {
          onSources(data.sources, data.session_id);
        } else if (data.type === "token") {
          onToken(data.content);
        } else if (data.type === "done") {
          onDone();
        }
      }
    }
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)));
  }
}

export async function getStats(): Promise<IndexStats> {
  const res = await fetch(`${API_BASE}/knowledge/stats`);
  return res.json();
}

export async function triggerSync(): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/sync`, { method: "POST" });
  return res.json();
}

export async function triggerFullSync(): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/sync/full`, { method: "POST" });
  return res.json();
}

export async function getSyncStatus(): Promise<SyncStatus> {
  const res = await fetch(`${API_BASE}/sync/status`);
  return res.json();
}

export async function ingestPDF(file: File): Promise<{ message: string; chunks: number }> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/knowledge/pdf`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`PDF upload failed: ${res.status}`);
  return res.json();
}

export async function ingestWeb(url: string, title?: string): Promise<{ message: string; chunks: number }> {
  const res = await fetch(`${API_BASE}/knowledge/web`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, title }),
  });
  if (!res.ok) throw new Error(`Web ingest failed: ${res.status}`);
  return res.json();
}
