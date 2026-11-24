const API_BASE = import.meta.env?.VITE_API_BASE || "";

function authHeaders() {
  const token = localStorage.getItem("travel_token") || "";
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchThreads() {
  if (!localStorage.getItem("travel_token")) return [];
  try {
    const res = await fetch(`${API_BASE}/api/threads`, { headers: authHeaders() });
    if (!res.ok) return [];
    const data = await res.json();
    return data.items || [];
  } catch {
    return [];
  }
}

export async function fetchThreadMessages(threadId) {
  try {
    const res = await fetch(`${API_BASE}/api/threads/${encodeURIComponent(threadId)}/messages`, {
      headers: authHeaders(),
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.messages || [];
  } catch {
    return [];
  }
}

export async function deleteThread(threadId) {
  try {
    const res = await fetch(`${API_BASE}/api/threads/${encodeURIComponent(threadId)}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    return res.ok;
  } catch {
    return false;
  }
}
