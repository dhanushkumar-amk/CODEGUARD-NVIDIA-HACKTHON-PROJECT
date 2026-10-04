import axios from 'axios';
import {
  CreatePRResponse,
  ProposedFix,
  ScanReport,
  ScanStartResponse,
  VerificationResult,
} from '../types';

export interface HealthResponse {
  status: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

/** Check backend health status */
export async function checkBackendHealth(): Promise<HealthResponse> {
  const response = await apiClient.get<HealthResponse>('/health');
  return response.data;
}

/** Initiate a new repository scan */
export async function startScan(
  repoUrl: string,
  branch: string = 'main'
): Promise<{ scan_id: string }> {
  const response = await apiClient.post<ScanStartResponse>('/api/scan/start', {
    repo_url: repoUrl,
    branch,
  });
  return { scan_id: response.data.scan_id };
}

/** Fetch synthesized fixes for a scan */
export async function getFixes(scanId: string): Promise<ProposedFix[]> {
  const response = await apiClient.get<ProposedFix[]>(`/api/fix/${scanId}`);
  return response.data;
}

/** Fetch sandbox verification results for a scan */
export async function getVerification(scanId: string): Promise<VerificationResult[]> {
  const response = await apiClient.get<VerificationResult[]>(`/api/verify/${scanId}`);
  return response.data;
}

/** Fetch the full consolidated audit report */
export async function getReport(scanId: string): Promise<ScanReport> {
  const response = await apiClient.get<ScanReport>(`/api/report/${scanId}`);
  return response.data;
}

/** Create a GitHub remediation branch and open a pull request */
export async function createRemediationPR(
  scanId: string,
  repoUrl?: string
): Promise<CreatePRResponse> {
  const response = await apiClient.post<CreatePRResponse>(
    `/api/report/${scanId}/create-pr`,
    repoUrl ? { repo_url: repoUrl } : {}
  );
  return response.data;
}
