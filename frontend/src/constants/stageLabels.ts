export interface PipelineStep {
  id: string;
  label: string;
  shortLabel: string;
  description: string;
  rawStages: string[];
}

export const PIPELINE_STEPS: PipelineStep[] = [
  {
    id: 'clone',
    label: 'Clone & Prepare',
    shortLabel: 'Clone',
    description: 'Fetch repository and extract scannable UI components',
    rawStages: ['init', 'cloning', 'preparing'],
  },
  {
    id: 'scan',
    label: 'Scan & Detect',
    shortLabel: 'Scan',
    description: 'AST parser & axe-core detect accessibility violations',
    rawStages: ['scanning'],
  },
  {
    id: 'classify',
    label: 'Classify & Rank',
    shortLabel: 'Classify',
    description: 'WCAG categorization, severity scoring & false-alarm pruning',
    rawStages: ['classifying', 'ranking'],
  },
  {
    id: 'grounding',
    label: 'Ground with WCAG',
    shortLabel: 'Ground',
    description: 'Tavily retrieves current WCAG 2.2 guidance & techniques',
    rawStages: ['grounding'],
  },
  {
    id: 'diagnose',
    label: 'Diagnose & Explain',
    shortLabel: 'Diagnose',
    description: 'Root-cause analysis and plain-English impact summaries',
    rawStages: ['diagnosing', 'explaining'],
  },
  {
    id: 'fix',
    label: 'Generate Fixes',
    shortLabel: 'Fixes',
    description: 'Nemotron Ultra synthesizes clean, idiomatic code diffs',
    rawStages: ['fixing', 'generating_fixes'],
  },
  {
    id: 'verify',
    label: 'Verify in Sandbox',
    shortLabel: 'Verify',
    description: 'Isolated Nebius sandboxes run Playwright & axe-core',
    rawStages: ['preparing_sandbox', 'applying_fix', 'testing_accessibility', 'verifying'],
  },
  {
    id: 'report',
    label: 'Consolidate Report',
    shortLabel: 'Report',
    description: 'Executive summary and compliance verification certificate',
    rawStages: ['complete', 'completed', 'finished'],
  },
];

const RAW_TO_STEP_MAP: Record<string, string> = {
  init: 'clone',
  cloning: 'clone',
  preparing: 'clone',
  scanning: 'scan',
  classifying: 'classify',
  ranking: 'classify',
  grounding: 'grounding',
  diagnosing: 'diagnose',
  explaining: 'diagnose',
  fixing: 'fix',
  generating_fixes: 'fix',
  preparing_sandbox: 'verify',
  applying_fix: 'verify',
  testing_accessibility: 'verify',
  verifying: 'verify',
  complete: 'report',
  completed: 'report',
  finished: 'report',
};

const STAGE_DISPLAY_NAMES: Record<string, string> = {
  init: 'Initializing Environment',
  cloning: 'Cloning Repository',
  preparing: 'Extracting Markup Chunks',
  scanning: 'Scanning Accessibility Rules',
  classifying: 'Classifying Severity & Priorities',
  grounding: 'Looking up WCAG guidance with Tavily',
  diagnosing: 'Diagnosing Root Causes',
  explaining: 'Generating Plain Explanations',
  fixing: 'Synthesizing Code Patches',
  generating_fixes: 'Synthesizing Code Patches',
  preparing_sandbox: 'Spinning Up Isolated Sandbox',
  applying_fix: 'Applying Patches in Sandbox',
  testing_accessibility: 'Executing axe-core Headless Checks',
  verifying: 'Verifying Compliance Proof',
  complete: 'Scan Complete — Verified',
  completed: 'Scan Complete — Verified',
};

/**
 * Returns the timeline step ID corresponding to a raw backend stage name.
 */
export function getStepIdForStage(stage: string): string {
  const normalized = stage.toLowerCase().trim();
  return RAW_TO_STEP_MAP[normalized] || 'clone';
}

/**
 * Returns the index (0..PIPELINE_STEPS.length - 1) of the active timeline step.
 */
export function getStepIndexForStage(stage: string): number {
  const stepId = getStepIdForStage(stage);
  const index = PIPELINE_STEPS.findIndex((s) => s.id === stepId);
  return index >= 0 ? index : 0;
}

/**
 * Returns a human-friendly display label for a raw backend stage.
 */
export function getStageDisplayLabel(stage: string): string {
  const normalized = stage.toLowerCase().trim();
  return STAGE_DISPLAY_NAMES[normalized] || stage.replace(/_/g, ' ');
}
