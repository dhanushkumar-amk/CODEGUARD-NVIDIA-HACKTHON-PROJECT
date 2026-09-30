/**
 * TypeScript Data Models mirroring backend Pydantic schemas.
 */

export type ViolationCategory =
  | 'MISSING_ALT_TEXT'
  | 'UNLABELED_FORM_FIELD'
  | 'NON_INTERACTIVE_CLICK'
  | 'EMPTY_LINK_OR_BUTTON'
  | 'LOW_CONTRAST'
  | 'HEADING_ORDER'
  | 'MISSING_LANDMARK'
  | 'KEYBOARD_TRAP'
  | 'MISSING_LANG'
  | 'ARIA_MISUSE'
  | 'FOCUS_MANAGEMENT'
  | 'OTHER';

export type SeverityLevel =
  | 'critical'
  | 'high'
  | 'medium'
  | 'low'
  | 'serious'
  | 'moderate'
  | 'minor';

export interface Violation {
  id: string;
  file: string;
  line?: number | null;
  type: string;
  severity: SeverityLevel | string;
  description: string;
  selector?: string | null;
  context_snippet?: string | null;
  source?: 'rule' | 'llm' | string;
  wcag_criterion?: string | null;
  category?: ViolationCategory | string;
  severity_score?: number | null;
  priority_rank?: number | null;
}

export interface DiagnosedViolation extends Violation {
  root_cause: string;
  affected_element: string;
  user_impact: string;
  fix_strategy: string;
  confidence: 'high' | 'medium' | 'low' | string;
  diagnosis_source: 'llm' | 'template' | string;
  plain_explanation?: string;
}

export interface ViolationSummary {
  total: number;
  by_category: Record<string, number>;
  by_severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
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
  summary?: ViolationSummary | null;
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
  repo_url?: string;
  branch?: string;
  file_count?: number;
  framework?: string;
  scannable_files?: string[];
  batch_count?: number;
}

export interface WebSocketMessage {
  stage: 'init' | 'cloning' | 'scanning' | 'diagnosing' | 'explaining' | 'fixing' | 'verifying' | 'completed' | 'error' | string;
  progress: number;
  message: string;
  data?: Record<string, any> | null;
  timestamp?: string;
}
