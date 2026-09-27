/**
 * TypeScript Data Models mirroring backend Pydantic schemas.
 */

export type SeverityLevel = 'critical' | 'serious' | 'moderate' | 'minor';

export interface Violation {
  id: string;
  file: string;
  line?: number | null;
  type: string;
  severity: SeverityLevel | string;
  description: string;
  selector?: string | null;
  context_snippet?: string | null;
}

export interface ProposedFix {
  fix_id: string;
  violation_id: string;
  diff: string;
  explanation: string;
  original_code?: string | null;
  remediated_code?: string | null;
}

export interface VerificationResult {
  fix_id: string;
  violation_id?: string | null;
  axe_score_before: number;
  axe_score_after: number;
  tests_passed: boolean;
  violations_resolved?: boolean;
  verified: boolean;
  sandbox_id?: string | null;
  sandbox_logs?: string | null;
}

export interface ScanReport {
  scan_id: string;
  repo_url: string;
  branch: string;
  violations: Violation[];
  fixes: ProposedFix[];
  verification_results: VerificationResult[];
  overall_score_before: number;
  overall_score_after: number;
  timestamp: string;
  status: string;
}

export interface ScanRequest {
  repo_url: string;
  branch?: string;
}

export interface ScanStartResponse {
  scan_id: string;
  status: string;
  message?: string;
}

export interface WebSocketMessage {
  stage: 'init' | 'cloning' | 'scanning' | 'fixing' | 'verifying' | 'completed' | 'error' | string;
  progress: number;
  message: string;
  data?: Record<string, any> | null;
  timestamp?: string;
}
