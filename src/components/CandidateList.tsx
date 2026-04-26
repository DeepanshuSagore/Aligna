"use client";

import { useEffect, useRef, useState } from "react";
import { UserCircle2, MapPin, Briefcase, ChevronRight, Download, ChevronLeft } from "lucide-react";
import { SkillPills } from "./SkillPills";
import { ScoreExplainer, type ScoreBreakdown } from "./ScoreExplainer";

export interface Candidate {
  id: string;
  name: string;
  role: string;
  skills: string[];
  years_experience: number;
  city: string;
  remote_preference: string;
  expected_salary: string;
  education: string;
  last_company: string;
  open_to_work: boolean;
  match_score: number;
  match_reason: string;
  score_breakdown?: ScoreBreakdown | null;
}

interface CandidateListProps {
  candidates: Candidate[];
  onEngage: (candidate: Candidate) => void;
  engagedIds?: Set<string>;
}

const ITEMS_PER_PAGE = 15;

export function CandidateList({ candidates, onEngage, engagedIds }: CandidateListProps) {
  const [includeAIReason, setIncludeAIReason] = useState(false);
  const [expandedScoreId, setExpandedScoreId] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const itemRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});

  useEffect(() => {
    if (expandedScoreId && itemRefs.current[expandedScoreId]) {
      setTimeout(() => {
        itemRefs.current[expandedScoreId]?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 100);
    }
  }, [expandedScoreId]);

  if (!candidates || candidates.length === 0) return null;

  const totalPages = Math.ceil(candidates.length / ITEMS_PER_PAGE);
  const paginatedCandidates = candidates.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  const handleExportCSV = () => {
    let csvContent = "";
    // Add BOM for Excel UTF-8 support
    const BOM = "\uFEFF";
    csvContent += BOM;

    const headers = ["Name", "Role", "Match Score", "Years Experience", "City", "Remote Preference", "Expected Salary", "Last Company", "Top Skills"];
    if (includeAIReason) {
      headers.push("AI Match Reason");
    }
    csvContent += headers.join(",") + "\n";

    candidates.forEach((c) => {
      const row = [
        `"${c.name}"`,
        `"${c.role}"`,
        c.match_score,
        c.years_experience,
        `"${c.city}"`,
        `"${c.remote_preference}"`,
        `"${c.expected_salary}"`,
        `"${c.last_company}"`,
        `"${c.skills.slice(0,5).join(", ")}"`
      ];
      if (includeAIReason) {
        row.push(`"${c.match_reason.replace(/"/g, '""')}"`);
      }
      csvContent += row.join(",") + "\n";
    });

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "aligna_shortlist.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-8 duration-700 pb-24">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-2 gap-4">
        <div>
          <h2 className="text-3xl font-fustat font-bold text-white drop-shadow-md">Top Matches</h2>
          <span className="text-white/60 text-sm font-medium">{candidates.length} candidates found</span>
        </div>
        <div className="flex items-center gap-4 bg-white/5 p-2 rounded-xl border border-white/10">
          <label className="flex items-center gap-2 text-xs text-white/70 cursor-pointer hover:text-white transition-colors">
            <input 
              type="checkbox" 
              checked={includeAIReason} 
              onChange={(e) => setIncludeAIReason(e.target.checked)}
              className="rounded bg-white/10 border-white/20 text-[#5AE14C] focus:ring-[#5AE14C] focus:ring-offset-0"
            />
            Include AI Reasons
          </label>
          <button 
            onClick={handleExportCSV}
            className="flex items-center gap-2 px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors text-sm font-medium"
          >
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-4">
        {paginatedCandidates.map((candidate, idx) => {
          const index = (currentPage - 1) * ITEMS_PER_PAGE + idx;
          const isScoreExpanded = expandedScoreId === candidate.id;
          return (
          <div 
            key={candidate.id}
            ref={(el) => { itemRefs.current[candidate.id] = el; }}
            className="group relative glassmorphism rounded-[24px] p-6 border border-white/10 hover:border-white/20 transition-all duration-300 hover:shadow-[0_15px_40px_rgba(0,0,0,0.4)] hover:-translate-y-1 flex flex-col md:flex-row gap-6 items-start md:items-center"
          >
            {/* Match Score Ring */}
            <div className="flex-shrink-0 relative w-20 h-20 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="40" cy="40" r="36" fill="transparent" stroke="rgba(255,255,255,0.1)" strokeWidth="6" />
                <circle 
                  cx="40" 
                  cy="40" 
                  r="36" 
                  fill="transparent" 
                  stroke={candidate.match_score >= 80 ? "#5AE14C" : candidate.match_score >= 60 ? "#FACC15" : "#F87171"} 
                  strokeWidth="6" 
                  strokeDasharray={`${(candidate.match_score / 100) * 226} 226`}
                  className="transition-all duration-1000 ease-out"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-xl font-bold text-white">{candidate.match_score}</span>
              </div>
              {/* Top match badge */}
              {index === 0 && (
                <div className="absolute -top-2 -right-2 bg-yellow-400 text-black text-[10px] font-bold px-2 py-0.5 rounded-full shadow-lg">
                  #1
                </div>
              )}
            </div>

            {/* Candidate Details */}
            <div className="flex-grow flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-semibold text-white flex items-center gap-2">
                  <UserCircle2 className="w-5 h-5 text-white/70" />
                  {candidate.name}
                </h3>
                <div className="hidden md:flex text-sm font-medium text-[#5AE14C] items-center gap-1.5 bg-[#5AE14C]/10 px-3 py-1 rounded-full border border-[#5AE14C]/20">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#5AE14C] animate-pulse"></span>
                  Ready to Engage
                </div>
              </div>
              
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-white/70 mt-1">
                <span className="flex items-center gap-1.5 font-medium text-white/90">
                  <Briefcase className="w-4 h-4" />
                  {candidate.role}
                </span>
                <span className="flex items-center gap-1.5">
                  <MapPin className="w-4 h-4" />
                  {candidate.city} ({candidate.remote_preference})
                </span>
                <span className="bg-white/10 px-2 py-0.5 rounded-md text-white/80 border border-white/5">
                  {candidate.years_experience} YOE
                </span>
                <span className="text-white/50 text-xs truncate max-w-[200px]">
                  Prev: {candidate.last_company}
                </span>
              </div>

              <div className="mt-3">
                <SkillPills skills={candidate.skills.slice(0, 6)} type="good-to-have" />
              </div>
              
              <p className="text-xs text-white/50 mt-1 italic">
                AI Note: {candidate.match_reason}
              </p>
              <button
                onClick={() => setExpandedScoreId(isScoreExpanded ? null : candidate.id)}
                className="mt-3 inline-flex items-center gap-2 rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-white/75 transition-colors hover:bg-white/10 hover:text-white"
              >
                {isScoreExpanded ? "Hide Score Explainer" : "Score Explainer"}
              </button>

              {isScoreExpanded && (
                <div className="mt-4">
                  <ScoreExplainer scoreBreakdown={candidate.score_breakdown} matchScore={candidate.match_score} />
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex-shrink-0 w-full md:w-auto mt-4 md:mt-0 flex flex-col items-center justify-center">
              {engagedIds?.has(candidate.id) ? (
                <div className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-[#5AE14C]/10 border border-[#5AE14C]/30 text-[#5AE14C] font-medium rounded-xl">
                  <span>✓ Engaged</span>
                </div>
              ) : (
                <button 
                  onClick={() => onEngage(candidate)}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white transition-colors group-hover:bg-white group-hover:text-black group-hover:border-transparent"
                >
                  <span>Engage</span>
                  <ChevronRight className="w-4 h-4" />
                </button>
              )}
              <span className="text-[10px] text-white/50 mt-2 uppercase tracking-widest hidden md:block text-center">
                AI Outreach
              </span>
            </div>
          </div>
          );
        })}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-10 flex items-center justify-center gap-4">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="p-2 rounded-lg bg-white/5 border border-white/10 text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/10 transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                onClick={() => setCurrentPage(page)}
                className={`w-10 h-10 rounded-lg flex items-center justify-center text-sm font-semibold transition-all ${
                  currentPage === page
                    ? "bg-[#5AE14C] text-black shadow-[0_0_15px_rgba(90,225,76,0.4)]"
                    : "bg-white/5 border border-white/10 text-white/70 hover:bg-white/10"
                }`}
              >
                {page}
              </button>
            ))}
          </div>
          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="p-2 rounded-lg bg-white/5 border border-white/10 text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/10 transition-colors"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      )}
    </div>
  );
}
