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
  file?: string;
  line_start?: number | null;
  line_end?: number | null;
  original_lines?: string;
  fixed_lines?: string;
  diff: string;
  explanation_of_change?: string;
  explanation?: string;
  confidence?: 'high' | 'medium' | 'low' | string;
  status?: 'proposed' | 'failed' | string;
  failure_reason?: string | null;
  original_code?: string | null;
  remediated_code?: string | null;
}

export interface VerificationResult {
  fix_id: string;
  violation_id?: string | null;
  axe_score_before: number;
  axe_score_after: number;
  violation_still_present?: boolean;
  tests_passed?: boolean | null;
  test_status?: 'passed' | 'failed' | 'timeout' | 'no_tests_found' | 'error' | string | null;
  violations_resolved?: boolean;
  verified: boolean;
  reason?: string | null;
  sandbox_id?: string | null;
  sandbox_logs?: string | null;
}

export interface TestRunResult {
  status: 'passed' | 'failed' | 'timeout' | 'no_tests_found' | 'error' | string;
  passed?: boolean | null;
  passed_count?: number | null;
  failed_count?: number | null;
  raw_output: string;
  duration_seconds: number;
}

export interface UnifiedViolationRecord {
  violation: DiagnosedViolation;
  fix?: ProposedFix | null;
  verification?: VerificationResult | null;
  final_status: 'fixed_and_verified' | 'fixed_not_verified' | 'fix_failed' | 'detected_only' | 'verification_skipped' | string;
}

export interface CostBreakdown {
  fast_cost: number;
  ultra_cost: number;
  total_cost: number;
}

export interface ScoreImprovement {
  score_before: number;
  score_after: number;
  improvement_points: number;
}

export interface ScanReport {
  scan_id: string;
  repo_url: string;
  branch: string;
  violations: Violation[];
  fixes: ProposedFix[];
  verification_results: VerificationResult[];
  unified_records?: UnifiedViolationRecord[];
  overall_score_before: number;
  overall_score_after: number;
  overall_improvement?: ScoreImprovement | null;
  summary?: any | null;
  executive_summary?: string | null;
  cost_breakdown?: CostBreakdown | null;
  total_duration_seconds?: number;
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

export interface CreatePRRequest {
  repo_url?: string;
}

export interface CreatePRResponse {
  pr_url?: string;
  files_changed?: number;
  status: 'success' | 'failed';
  error?: string;
}
