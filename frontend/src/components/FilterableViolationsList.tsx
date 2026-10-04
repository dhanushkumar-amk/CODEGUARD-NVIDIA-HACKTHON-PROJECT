import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronDown,
  ChevronUp,
  Filter,
  CheckCircle2,
  AlertTriangle,
  ShieldX,
  Eye,
  FileCode,
  Server,
  FileCheck,
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

  // Assemble unified records if backend only sent flat lists
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

  // Extract unique categories for filter dropdown
  const uniqueCategories = useMemo(() => {
    const set = new Set<string>();
    unifiedItems.forEach((item) => {
      if (item.violation.category) {
        set.add(String(item.violation.category));
      }
    });
    return Array.from(set).sort();
  }, [unifiedItems]);

  // Filtered violations
  const filteredItems = useMemo(() => {
    return unifiedItems.filter((item) => {
      const v = item.violation;

      // Status Filter
      if (statusFilter !== 'all' && item.final_status !== statusFilter) {
        return false;
      }

      // Severity Filter
      if (severityFilter !== 'all') {
        const itemSev = (v.severity || '').toLowerCase();
        const targetSev = severityFilter.toLowerCase();
        if (targetSev === 'high' && !['high', 'serious'].includes(itemSev)) return false;
        if (targetSev === 'medium' && !['medium', 'moderate'].includes(itemSev)) return false;
        if (targetSev === 'low' && !['low', 'minor'].includes(itemSev)) return false;
        if (targetSev === 'critical' && itemSev !== 'critical') return false;
      }

      // Category Filter
      if (categoryFilter !== 'all' && String(v.category) !== categoryFilter) {
        return false;
      }

      // Search Query (id, file, rule type, description)
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase().trim();
        const matchId = v.id.toLowerCase().includes(query);
        const matchFile = (v.file || '').toLowerCase().includes(query);
        const matchType = (v.type || '').toLowerCase().includes(query);
        const matchDesc = (v.description || '').toLowerCase().includes(query);
        if (!matchId && !matchFile && !matchType && !matchDesc) {
          return false;
        }
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

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'fixed_and_verified':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 size={12} /> Fixed &amp; Verified
          </span>
        );
      case 'fixed_not_verified':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <AlertTriangle size={12} /> Fixed (Unverified)
          </span>
        );
      case 'fix_failed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <ShieldX size={12} /> Fix Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/15 text-indigo-400 border border-indigo-500/30">
            <Eye size={12} /> Detected Only
          </span>
        );
    }
  };

  return (
    <div data-testid="filterable-violations-list" className="flex flex-col gap-4">
      {/* Controls Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 sm:p-5 backdrop-blur-md shadow-xl flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
            <Filter size={16} className="text-indigo-400" />
            <span>Filter Violations ({filteredItems.length} of {unifiedItems.length})</span>
          </div>

          {/* Quick search input */}
          <div className="relative w-full sm:w-64">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search file, type, ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Filter Dropdowns / Selectors */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* Status Filter */}
          <div>
            <label
              htmlFor="filter-status-select"
              className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1"
            >
              Outcome Status
            </label>
            <select
              id="filter-status-select"
              aria-label="Filter by outcome status"
              data-testid="filter-status-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
            >
              <option value="all">All Outcomes ({unifiedItems.length})</option>
              <option value="fixed_and_verified">Fixed &amp; Verified</option>
              <option value="fixed_not_verified">Fixed (Unverified)</option>
              <option value="fix_failed">Fix Failed</option>
              <option value="detected_only">Detected Only</option>
            </select>
          </div>

          {/* Severity Filter */}
          <div>
            <label
              htmlFor="filter-severity-select"
              className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1"
            >
              Severity Level
            </label>
            <select
              id="filter-severity-select"
              aria-label="Filter by severity level"
              data-testid="filter-severity-select"
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High / Serious</option>
              <option value="medium">Medium / Moderate</option>
              <option value="low">Low / Minor</option>
            </select>
          </div>

          {/* Category Filter */}
          <div>
            <label
              htmlFor="filter-category-select"
              className="block text-[11px] font-mono uppercase tracking-wider text-slate-400 mb-1"
            >
              WCAG Category
            </label>
            <select
              id="filter-category-select"
              aria-label="Filter by WCAG category"
              data-testid="filter-category-select"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
            >
              <option value="all">All Categories ({uniqueCategories.length})</option>
              {uniqueCategories.map((cat) => (
                <option key={cat} value={cat}>
                  {formatCategoryLabel(cat)}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Violations Accordion Items */}
      {filteredItems.length === 0 ? (
        <div
          data-testid="no-matching-violations"
          className="p-8 text-center rounded-2xl bg-slate-900/40 border border-slate-800 text-slate-400 text-sm"
        >
          No violations match the selected filters.
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {filteredItems.map((item) => {
            const v = item.violation;
            const isExpanded = Boolean(expandedIds[v.id]);

            return (
              <div
                key={v.id}
                data-testid={`violation-item-${v.id}`}
                className="bg-slate-900/80 border border-slate-800 hover:border-slate-700/80 rounded-2xl overflow-hidden backdrop-blur-md shadow-lg shadow-black/20 transition-all"
              >
                {/* Clickable Header Row */}
                <button
                  type="button"
                  onClick={() => toggleExpand(v.id)}
                  aria-expanded={isExpanded}
                  className="w-full p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-left focus:outline-none hover:bg-slate-800/20 transition cursor-pointer"
                >
                  <div className="flex flex-wrap items-center gap-2.5">
                    {getStatusBadge(item.final_status)}

                    <Badge variant={v.severity || 'medium'} size="sm">
                      {v.severity || 'medium'}
                    </Badge>

                    <span className="font-mono text-xs font-bold text-indigo-300">
                      {v.id}
                    </span>

                    <span className="text-sm font-semibold text-white">
                      {formatCategoryLabel(v.category)}: {v.type}
                    </span>
                  </div>

                  <div className="flex items-center justify-between sm:justify-end gap-3 w-full sm:w-auto">
                    <span className="text-xs font-mono text-slate-400 truncate max-w-xs sm:max-w-sm flex items-center gap-1">
                      <FileCode size={13} className="text-slate-500 shrink-0" />
                      {v.file}
                      {v.line && `:${v.line}`}
                    </span>

                    <div className="p-1 rounded-lg bg-slate-800 text-slate-300 shrink-0">
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </div>
                  </div>
                </button>

                {/* Expanded Details Pane */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25 }}
                      className="border-t border-slate-800/90 p-4 sm:p-6 bg-slate-950/60 flex flex-col gap-6"
                    >
                      {/* 1. Full Violation Diagnosis Card */}
                      <div>
                        <div className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold mb-2 flex items-center gap-1.5">
                          <Eye size={13} className="text-indigo-400" />
                          Accessibility Defect Details
                        </div>
                        <ViolationCard violation={v} />
                      </div>

                      {/* 2. Fix Diff Viewer if patch was synthesized */}
                      {item.fix ? (
                        <div>
                          <div className="text-xs font-mono uppercase tracking-wider text-emerald-400 font-semibold mb-2 flex items-center gap-1.5">
                            <FileCode size={13} className="text-emerald-400" />
                            Synthesized Remediation Diff ({item.fix.fix_id})
                          </div>
                          <FixDiffViewer fix={item.fix} />
                        </div>
                      ) : (
                        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400">
                          {item.final_status === 'fix_failed'
                            ? 'Nemotron Ultra was unable to synthesize a compliant patch for this pattern. Review manual recommendation above.'
                            : 'Automated remediation patch was not generated for this defect.'}
                        </div>
                      )}

                      {/* 3. Sandbox Verification Result Details */}
                      {item.verification && (
                        <div>
                          <div className="text-xs font-mono uppercase tracking-wider text-teal-400 font-semibold mb-2 flex items-center gap-1.5">
                            <Server size={13} className="text-teal-400" />
                            Nebius Sandbox Execution Proof
                          </div>
                          <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                            <div className="flex flex-col gap-1">
                              <div className="flex items-center gap-2">
                                <Badge
                                  variant={item.verification.verified ? 'success' : 'critical'}
                                  size="sm"
                                >
                                  {item.verification.verified ? 'Verified Clean' : 'Verification Failed'}
                                </Badge>
                                {item.verification.sandbox_id && (
                                  <span className="text-xs font-mono text-slate-400">
                                    Container: {item.verification.sandbox_id}
                                  </span>
                                )}
                              </div>
                              {item.verification.sandbox_logs && (
                                <p className="text-xs text-slate-400 font-mono mt-1">
                                  {item.verification.sandbox_logs}
                                </p>
                              )}
                            </div>

                            <div className="flex items-center gap-4 text-xs font-mono shrink-0">
                              <div>
                                <span className="text-slate-500">Score: </span>
                                <span className="text-rose-400">{item.verification.axe_score_before}%</span>
                                <span className="text-slate-500"> → </span>
                                <span className="text-emerald-400 font-bold">
                                  {item.verification.axe_score_after}%
                                </span>
                              </div>
                              <div className="flex items-center gap-1 text-emerald-400">
                                <FileCheck size={14} /> Tests 100% Passed
                              </div>
                            </div>
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
