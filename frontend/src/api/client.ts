export interface HealthResponse {
  status: string;
}

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

export async function checkBackendHealth(): Promise<HealthResponse> {
  // First try direct backend URL, then fallback to proxy
  try {
    const res = await fetch(`${BACKEND_URL}/health`, {
      headers: {
        'Accept': 'application/json',
      },
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    return await res.json();
  } catch (directError) {
    // Attempt fallback via Vite proxy if direct connection fails
    try {
      const fallbackRes = await fetch('/api/health');
      if (!fallbackRes.ok) {
        throw new Error(`Fallback HTTP ${fallbackRes.status}`);
      }
      return await fallbackRes.json();
    } catch {
      throw directError;
    }
  }
}
