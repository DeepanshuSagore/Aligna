"use client";

import { useEffect, useRef, useState } from "react";
import {
  Trophy,
  Download,
  MessageSquare,
  TrendingUp,
  Target,
  Award,
  ChevronDown,
  ChevronUp,
  UserCircle2,
  Briefcase,
  MapPin,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { type Candidate } from "./CandidateList";
import { ScoreExplainer } from "./ScoreExplainer";

export interface EngagedCandidate extends Candidate {
  interest_score: number;
  final_score: number;
  chat_logs: { sender: string; message: string }[];
  interest_reason: string;
  interest_factors: string[];
}

interface RankedShortlistProps {
  candidates: EngagedCandidate[];
}

const ITEMS_PER_PAGE = 15;

export function RankedShortlist({ candidates }: RankedShortlistProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const itemRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});

  useEffect(() => {
    if (expandedId && itemRefs.current[expandedId]) {
      setTimeout(() => {
        itemRefs.current[expandedId]?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }, 100);
    }
  }, [expandedId]);

  if (!candidates || candidates.length === 0) return null;

  // Sort by final_score descending
  const sorted = [...candidates].sort((a, b) => b.final_score - a.final_score);

  const totalPages = Math.ceil(sorted.length / ITEMS_PER_PAGE);
  const paginatedCandidates = sorted.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  const handleExportCSV = () => {
    let csvContent = "\uFEFF"; // BOM for Excel
    const headers = [
      "Rank",
      "Name",
      "Role",
      "Match Score",
      "Interest Score",
      "Final Score",
      "City",
      "Remote Preference",
      "Expected Salary",
      "Top Skills",
      "AI Match Reason",
      "Interest Reason",
    ];
    csvContent += headers.join(",") + "\n";

    sorted.forEach((c, i) => {
      const row = [
        i + 1,
        `"${c.name}"`,
        `"${c.role}"`,
        c.match_score,
        c.interest_score,
        c.final_score,
        `"${c.city}"`,
        `"${c.remote_preference}"`,
        `"${c.expected_salary}"`,
        `"${c.skills.slice(0, 5).join(", ")}"`,
        `"${(c.match_reason || "").replace(/"/g, '""')}"`,
        `"${(c.interest_reason || "").replace(/"/g, '""')}"`,
      ];
      csvContent += row.join(",") + "\n";
    });

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "aligna_ranked_shortlist.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const getTierColor = (score: number) => {
    if (score >= 75) return { bg: "bg-[#5AE14C]/10", border: "border-[#5AE14C]/30", text: "text-[#5AE14C]", label: "Hot Lead" };
    if (score >= 55) return { bg: "bg-[#FACC15]/10", border: "border-[#FACC15]/30", text: "text-[#FACC15]", label: "Warm" };
    return { bg: "bg-[#F87171]/10", border: "border-[#F87171]/30", text: "text-[#F87171]", label: "Cold" };
  };

  return (
    <div className="w-full max-w-[1400px] mx-auto animate-in fade-in slide-in-from-bottom-8 duration-700 pb-24">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-8 gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-[#5AE14C]/10 flex items-center justify-center border border-[#5AE14C]/20">
            <Trophy className="w-6 h-6 text-[#5AE14C]" />
          </div>
          <div>
            <h2 className="text-3xl font-fustat font-bold text-white drop-shadow-md">
              Final Ranked Shortlist
            </h2>
            <p className="text-white/50 text-sm font-medium">
              {sorted.length} candidates scored • Formula: 0.7×Match + 0.3×Interest
            </p>
          </div>
        </div>
        <button
          onClick={handleExportCSV}
          className="flex items-center gap-2 px-5 py-2.5 bg-[#5AE14C] text-black font-semibold rounded-xl hover:bg-[#4DC93F] transition-all shadow-[0_0_20px_rgba(90,225,76,0.3)] hover:shadow-[0_0_30px_rgba(90,225,76,0.5)]"
        >
          <Download className="w-4 h-4" />
          Export Shortlist
        </button>
      </div>

      {/* Score Summary Cards */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="glassmorphism p-5 rounded-[18px] border border-[#5AE14C]/20 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-[#5AE14C]" />
            <span className="text-xs font-semibold text-white/50 uppercase tracking-wider">Avg Match</span>
          </div>
          <span className="text-2xl font-bold text-white">
            {Math.round(sorted.reduce((s, c) => s + c.match_score, 0) / sorted.length)}
          </span>
        </div>
        <div className="glassmorphism p-5 rounded-[18px] border border-blue-500/20 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Target className="w-4 h-4 text-blue-400" />
            <span className="text-xs font-semibold text-white/50 uppercase tracking-wider">Avg Interest</span>
          </div>
          <span className="text-2xl font-bold text-white">
            {Math.round(sorted.reduce((s, c) => s + c.interest_score, 0) / sorted.length)}
          </span>
        </div>
        <div className="glassmorphism p-5 rounded-[18px] border border-[#5AE14C]/30 bg-[#5AE14C]/5 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Award className="w-4 h-4 text-[#5AE14C]" />
            <span className="text-xs font-semibold text-[#5AE14C]/70 uppercase tracking-wider">Avg Final</span>
          </div>
          <span className="text-2xl font-bold text-[#5AE14C] drop-shadow-[0_0_10px_rgba(90,225,76,0.4)]">
            {Math.round(sorted.reduce((s, c) => s + c.final_score, 0) / sorted.length)}
          </span>
        </div>
      </div>

      {/* Ranked Cards */}
      <div className="flex flex-col gap-4">
        {paginatedCandidates.map((candidate, idx) => {
          const index = (currentPage - 1) * ITEMS_PER_PAGE + idx;
          const tier = getTierColor(candidate.final_score);
          const isExpanded = expandedId === candidate.id;
          const interestReason = candidate.interest_reason ?? "";
          const interestFactors = candidate.interest_factors ?? [];

          return (
            <div
              key={candidate.id}
              ref={(el) => (itemRefs.current[candidate.id] = el)}
              className={`glassmorphism rounded-[20px] border transition-all duration-300 hover:shadow-[0_15px_40px_rgba(0,0,0,0.4)] ${
                index === 0
                  ? "border-[#5AE14C]/30 shadow-[0_0_30px_rgba(90,225,76,0.1)]"
                  : "border-white/10 hover:border-white/20"
              }`}
            >
              {/* Main Row */}
              <div className="p-6 flex flex-col md:flex-row items-start md:items-center gap-5">
                {/* Rank Badge */}
                <div
                  className={`flex-shrink-0 w-12 h-12 rounded-2xl flex items-center justify-center font-bold text-lg ${
                    index === 0
                      ? "bg-yellow-400 text-black shadow-[0_0_15px_rgba(250,204,21,0.4)]"
                      : index === 1
                      ? "bg-gray-300 text-black"
                      : index === 2
                      ? "bg-amber-700 text-white"
                      : "bg-white/10 text-white/70 border border-white/10"
                  }`}
                >
                  #{index + 1}
                </div>

                {/* Candidate Info */}
                <div className="flex-grow min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2 truncate">
                      <UserCircle2 className="w-5 h-5 text-white/70 flex-shrink-0" />
                      {candidate.name}
                    </h3>
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${tier.bg} ${tier.border} ${tier.text} border flex-shrink-0`}>
                      {tier.label}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-white/60">
                    <span className="flex items-center gap-1.5">
                      <Briefcase className="w-3.5 h-3.5" />
                      {candidate.role}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5" />
                      {candidate.city}
                    </span>
                  </div>
                </div>

                {/* Score Columns */}
                <div className="flex items-center gap-6 flex-shrink-0">
                  <div className="text-center">
                    <p className="text-[10px] font-semibold text-white/40 uppercase tracking-wider mb-1">Match</p>
                    <p className="text-xl font-bold text-white">{candidate.match_score}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-[10px] font-semibold text-white/40 uppercase tracking-wider mb-1">Interest</p>
                    <p className={`text-xl font-bold ${candidate.interest_score >= 70 ? "text-[#5AE14C]" : candidate.interest_score >= 40 ? "text-[#FACC15]" : "text-[#F87171]"}`}>
                      {candidate.interest_score}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-[10px] font-semibold text-[#5AE14C]/60 uppercase tracking-wider mb-1">Final</p>
                    <p className="text-2xl font-bold text-[#5AE14C] drop-shadow-[0_0_8px_rgba(90,225,76,0.4)]">
                      {candidate.final_score}
                    </p>
                  </div>
                </div>

                {/* Expand Button */}
                <button
                  onClick={() => setExpandedId(isExpanded ? null : candidate.id)}
                  className="flex-shrink-0 p-2 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-colors"
                >
                  {isExpanded ? (
                    <ChevronUp className="w-5 h-5 text-white/70" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-white/70" />
                  )}
                </button>
              </div>

              {/* Expanded: Chat Log */}
              {isExpanded && candidate.chat_logs && (
                <div className="px-6 pb-6 pt-2 border-t border-white/5">
                  <div className="mb-5">
                    <ScoreExplainer
                      scoreBreakdown={candidate.score_breakdown}
                      matchScore={candidate.match_score}
                    />
                  </div>
                  {(interestReason || interestFactors.length > 0) && (
                    <div className="mb-5 rounded-xl border border-blue-500/20 bg-blue-500/10 p-4">
                      <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-200">
                        <Target className="h-3.5 w-3.5" />
                        Interest Rationale
                      </p>
                      {interestReason && (
                        <p className="text-sm leading-relaxed text-white/80">{interestReason}</p>
                      )}
                      {interestFactors.length > 0 && (
                        <ul className="mt-3 space-y-1.5 text-xs text-white/65">
                          {interestFactors.map((factor) => (
                            <li key={factor} className="flex gap-2">
                              <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-blue-300/80" />
                              <span>{factor}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                  <div className="flex items-center gap-2 mb-4">
                    <MessageSquare className="w-4 h-4 text-white/50" />
                    <span className="text-sm font-semibold text-white/70">Outreach Conversation</span>
                  </div>
                  <div className="flex flex-col gap-3 ml-2">
                    {candidate.chat_logs.map((msg, i) => {
                      const isScout = msg.sender === "ALIGNA";
                      return (
                        <div
                          key={i}
                          className={`flex gap-3 ${isScout ? "justify-start" : "justify-end"}`}
                        >
                          <div
                            className={`max-w-[75%] p-3 rounded-xl text-sm ${
                              isScout
                                ? "bg-white/10 text-white/90 rounded-tl-sm border border-white/5"
                                : "bg-blue-600/25 text-white rounded-tr-sm border border-blue-500/20"
                            }`}
                          >
                            <p className="text-[10px] text-white/40 mb-0.5 font-medium">{msg.sender}</p>
                            <p className="leading-relaxed">{msg.message}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  {candidate.match_reason && (
                    <p className="text-xs text-white/40 mt-4 italic">
                      AI Note: {candidate.match_reason}
                    </p>
                  )}
                </div>
              )}
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
