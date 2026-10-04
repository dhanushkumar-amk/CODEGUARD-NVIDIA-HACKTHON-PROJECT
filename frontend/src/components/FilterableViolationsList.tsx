import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  AlertTriangle,
  ShieldX,
  Eye,
  FileCode,
  Search,
} from 'lucide-react';
import { UnifiedViolationRecord, Violation, ProposedFix, VerificationResult } from '../types';
import { Badge } from './Badge';
import { ViolationCard, formatCategoryLabel } from './ViolationCard';
import { FixDiffViewer } from './FixDiffViewer';

export interface FilterableViolationsListProps {
  records?: UnifiedViolationRecord[];
  fallbackViolations?: Violation[];
  fallbackFixes?: ProposedFix[];
  fallbackVerifications?: VerificationResult[];
}

export const FilterableViolationsList: React.FC<FilterableViolationsListProps> = ({
  records,
  fallbackViolations = [],
  fallbackFixes = [],
  fallbackVerifications = [],
}) => {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [expandedIds, setExpandedIds] = useState<Record<string, boolean>>({});

  const unifiedItems: UnifiedViolationRecord[] = useMemo(() => {
    if (records && records.length > 0) {
      return records;
    }

    const fixMap: Record<string, ProposedFix> = {};
    fallbackFixes.forEach((f) => {
      if (f.violation_id) fixMap[f.violation_id] = f;
    });

    const verifMap: Record<string, VerificationResult> = {};
    fallbackVerifications.forEach((vr) => {
      if (vr.fix_id) verifMap[vr.fix_id] = vr;
    });

    return fallbackViolations.map((v) => {
      const matchingFix = fixMap[v.id];
      const matchingVerif = matchingFix ? verifMap[matchingFix.fix_id] : undefined;

      let final_status = 'detected_only';
      if (matchingFix) {
        if (matchingFix.status === 'failed') {
          final_status = 'fix_failed';
        } else if (matchingVerif) {
          final_status = matchingVerif.verified ? 'fixed_and_verified' : 'fixed_not_verified';
        } else {
          final_status = 'verification_skipped';
        }
      }

      return {
        violation: v as any,
        fix: matchingFix,
        verification: matchingVerif,
        final_status,
      };
    });
  }, [records, fallbackViolations, fallbackFixes, fallbackVerifications]);

  const uniqueCategories = useMemo(() => {
    const set = new Set<string>();
    unifiedItems.forEach((item) => {
      if (item.violation.category) {
        set.add(String(item.violation.category));
      }
    });
    return Array.from(set).sort();
  }, [unifiedItems]);

  const filteredItems = useMemo(() => {
    return unifiedItems.filter((item) => {
      const v = item.violation;

      if (statusFilter !== 'all' && item.final_status !== statusFilter) {
        return false;
      }

      if (severityFilter !== 'all') {
        const itemSev = (v.severity || '').toLowerCase();
        const targetSev = severityFilter.toLowerCase();
        if (targetSev === 'high' && !['high', 'serious'].includes(itemSev)) return false;
        if (targetSev === 'medium' && !['medium', 'moderate'].includes(itemSev)) return false;
        if (targetSev === 'low' && !['low', 'minor'].includes(itemSev)) return false;
        if (targetSev === 'critical' && itemSev !== 'critical') return false;
      }

      if (categoryFilter !== 'all' && v.category !== categoryFilter) {
        return false;
      }

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const ruleMatch = (v.type || '').toLowerCase().includes(q);
        const descMatch = (v.description || '').toLowerCase().includes(q);
        const fileMatch = (v.file || '').toLowerCase().includes(q);
        const idMatch = (v.id || '').toLowerCase().includes(q);
        const catMatch = formatCategoryLabel(v.category).toLowerCase().includes(q);
        return ruleMatch || descMatch || fileMatch || idMatch || catMatch;
      }

      return true;
    });
  }, [unifiedItems, statusFilter, severityFilter, categoryFilter, searchQuery]);

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const getStatusIndicator = (status?: string) => {
    switch (status) {
      case 'fixed_and_verified':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] text-emerald font-medium">
            <CheckCircle2 size={12} className="text-emerald" /> Verified
          </span>
        );
      case 'fixed_not_verified':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] text-amber font-medium">
            <AlertTriangle size={12} className="text-amber" /> Unverified
          </span>
        );
      case 'fix_failed':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] text-coral font-medium">
            <ShieldX size={12} className="text-coral" /> Fix failed
          </span>
        );
      case 'verification_skipped':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] text-muted font-medium">
            Skipped
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[11px] text-muted font-medium">
            <Eye size={12} /> Detected
          </span>
        );
    }
  };

  return (
    <div
      data-testid="filterable-violations-list"
      className="w-full flex flex-col font-sans"
    >
      {/* Search and Filters Bar */}
      <div className="border border-line bg-paper p-4 flex flex-col gap-3">
        {/* Search */}
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="text"
            data-testid="violations-search-input"
            placeholder="Search by rule, description, or file..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-control bg-paper border border-line text-xs text-ink placeholder:text-muted focus:outline-none focus:border-azure font-mono"
          />
        </div>

        {/* Filter dropdowns */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label
              htmlFor="filter-status-select"
              className="block text-[11px] text-muted mb-1"
            >
              Remediation status
            </label>
            <select
              id="filter-status-select"
              aria-label="Filter by remediation status"
              data-testid="filter-status-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-1.5 rounded-control bg-paper border border-line text-xs text-ink focus:outline-none focus:border-azure font-mono cursor-pointer"
            >
              <option value="all">All statuses</option>
              <option value="fixed_and_verified">Fixed &amp; verified</option>
              <option value="fixed_not_verified">Fixed (unverified)</option>
              <option value="detected_only">Detected only</option>
              <option value="fix_failed">Fix failed</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="filter-severity-select"
              className="block text-[11px] text-muted mb-1"
            >
              Severity level
            </label>
            <select
              id="filter-severity-select"
              aria-label="Filter by severity level"
              data-testid="filter-severity-select"
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="w-full px-3 py-1.5 rounded-control bg-paper border border-line text-xs text-ink focus:outline-none focus:border-azure font-mono cursor-pointer"
            >
              <option value="all">All severities</option>
              <option value="critical">Critical</option>
              <option value="high">High / serious</option>
              <option value="medium">Medium / moderate</option>
              <option value="low">Low / minor</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="filter-category-select"
              className="block text-[11px] text-muted mb-1"
            >
              WCAG category
            </label>
            <select
              id="filter-category-select"
              aria-label="Filter by WCAG category"
              data-testid="filter-category-select"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full px-3 py-1.5 rounded-control bg-paper border border-line text-xs text-ink focus:outline-none focus:border-azure font-mono cursor-pointer"
            >
              <option value="all">All categories ({uniqueCategories.length})</option>
              {uniqueCategories.map((cat) => (
                <option key={cat} value={cat}>
                  {formatCategoryLabel(cat)}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Violations audit log table */}
      {filteredItems.length === 0 ? (
        <div
          data-testid="no-matching-violations"
          className="p-8 text-center border border-line border-t-0 text-muted text-sm bg-[#FFFFFF]"
        >
          No violations match the selected filters.
        </div>
      ) : (
        <div className="border border-line border-t-0 divide-y divide-line bg-[#FFFFFF]">
          {/* Table header */}
          <div className="hidden sm:grid sm:grid-cols-[1fr_auto_auto_auto_auto] gap-4 px-4 py-2 bg-surface-1 text-[11px] text-muted font-medium border-b border-line">
            <span>Violation</span>
            <span className="w-20 text-center">Severity</span>
            <span className="w-24 text-center">Status</span>
            <span className="w-48">File</span>
            <span className="w-8"></span>
          </div>

          {filteredItems.map((item) => {
            const v = item.violation;
            const isExpanded = Boolean(expandedIds[v.id]);
            const severity = (v.severity || 'medium').toLowerCase();

            // 3px colored LEFT BORDER stripe matching severity (coral/amber-high/amber-medium/grey-low)
            const leftStripeClass =
              severity === 'critical'
                ? 'border-l-[3px] border-l-coral'
                : ['high', 'serious'].includes(severity)
                ? 'border-l-[3px] border-l-amber'
                : ['medium', 'moderate'].includes(severity)
                ? 'border-l-[3px] border-l-amber'
                : 'border-l-[3px] border-l-[#6C707A]';

            return (
              <div
                key={v.id}
                data-testid={`violation-item-${v.id}`}
                className={leftStripeClass}
              >
                {/* Row */}
                <button
                  type="button"
                  onClick={() => toggleExpand(v.id)}
                  aria-expanded={isExpanded}
                  className="w-full px-4 py-3 flex flex-col sm:grid sm:grid-cols-[1fr_auto_auto_auto_auto] sm:items-center gap-2 sm:gap-4 text-left focus:outline-none hover:bg-surface-1/40 transition-colors cursor-pointer"
                >
                  {/* Violation name + ID */}
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="font-mono text-[11px] text-muted shrink-0">{v.id}</span>
                    <span className="text-sm font-medium text-ink truncate">
                      {formatCategoryLabel(v.category)}: {v.type}
                    </span>
                  </div>

                  {/* Severity badge with purposeful soft tint */}
                  <div className="w-20 flex justify-center">
                    <Badge variant={v.severity as any || 'medium'} size="sm">
                      {v.severity || 'medium'}
                    </Badge>
                  </div>

                  {/* Status */}
                  <div className="w-24 flex justify-center">
                    {getStatusIndicator(item.final_status)}
                  </div>

                  {/* File path */}
                  <span className="w-48 text-xs font-mono text-muted truncate flex items-center gap-1">
                    <FileCode size={12} className="shrink-0" />
                    {v.file}
                    {v.line && `:${v.line}`}
                  </span>

                  {/* Expand chevron */}
                  <div className="w-8 flex justify-center text-muted">
                    {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </div>
                </button>

                {/* Expanded details */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="border-t border-line px-4 py-4 bg-surface-1/30 flex flex-col gap-4"
                    >
                      {/* Violation details */}
                      <div>
                        <div className="text-xs text-muted font-medium mb-2">
                          Defect details
                        </div>
                        <ViolationCard violation={v} />
                      </div>

                      {/* Fix diff */}
                      {item.fix ? (
                        <div>
                          <div className="text-xs text-muted font-medium mb-2">
                            Synthesized remediation ({item.fix.fix_id})
                          </div>
                          <FixDiffViewer fix={item.fix} />
                        </div>
                      ) : (
                        <div className="p-3 border border-line text-xs text-muted">
                          {item.final_status === 'fix_failed'
                            ? 'Nemotron Ultra was unable to synthesize a compliant patch for this pattern.'
                            : 'Automated remediation patch was not generated for this defect.'}
                        </div>
                      )}

                      {/* Verification */}
                      {item.verification && (
                        <div>
                          <div className="text-xs text-muted font-medium mb-2">
                            Sandbox verification
                          </div>
                          <div className="p-3 border border-line flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                            <div className="flex items-center gap-2">
                              {item.verification.verified ? (
                                <CheckCircle2 size={16} className="text-emerald shrink-0" />
                              ) : (
                                <AlertTriangle size={16} className="text-coral shrink-0" />
                              )}
                              <span className="text-xs text-ink font-medium">
                                {item.verification.verified
                                  ? 'Verified in isolated Nebius sandbox — zero regressions'
                                  : 'Verification failed in execution sandbox'}
                              </span>
                            </div>
                            {item.verification.axe_raw_output && (
                              <span className="text-[11px] font-mono text-muted">
                                axe-core score: {item.verification.axe_raw_output.violations_after ?? 0} remaining violations
                              </span>
                            )}
                          </div>
                        </div>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
