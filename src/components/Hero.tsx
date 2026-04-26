"use client";

import { useState, useCallback } from "react";
import { Sparkles, Zap, Users } from "lucide-react";
import { JDInputCard } from "./JDInputCard";
import { FeatureCards } from "./FeatureCards";
import { JDResults, type JDData } from "./JDResults";
import { CandidateList, type Candidate } from "./CandidateList";
import { EngagementModal } from "./EngagementModal";
import { PipelineSteps, type PipelineStep } from "./PipelineSteps";
import { RankedShortlist, type EngagedCandidate } from "./RankedShortlist";

export function Hero() {
  const [isLoading, setIsLoading] = useState(false);
  const [isMatching, setIsMatching] = useState(false);
  const [jdData, setJdData] = useState<JDData | null>(null);
  const [candidates, setCandidates] = useState<Candidate[] | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [pipelineStep, setPipelineStep] = useState<PipelineStep>("idle");

  // Track engaged candidates with their scores
  const [engagedCandidates, setEngagedCandidates] = useState<Map<string, EngagedCandidate>>(new Map());
  const [isEngagingAll, setIsEngagingAll] = useState(false);
  const [engageProgress, setEngageProgress] = useState({ current: 0, total: 0 });
  const [showRankedShortlist, setShowRankedShortlist] = useState(false);
  const totalCandidates = candidates?.length ?? 0;
  const remainingToEngage = Math.max(totalCandidates - engagedCandidates.size, 0);

  const handleAnalyzeText = async (jdText: string) => {
    setIsLoading(true);
    setJdData(null);
    setPipelineStep("parsing");
    setEngagedCandidates(new Map());
    setShowRankedShortlist(false);
    try {
      const res = await fetch(`/api/parse-jd`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ job_description: jdText }),
      });

      if (!res.ok) {
        const errorPayload = await res.json().catch(() => null);
        throw new Error(errorPayload?.detail || "Failed to parse JD");
      }

      const data: JDData = await res.json();
      setJdData(data);
      setCandidates(null);
      await handleFindMatches(data);
    } catch (error) {
      console.error(error);
      setPipelineStep("idle");
      const errorMessage = error instanceof Error ? error.message : "Unknown parsing error";
      alert(`Failed to analyze the Job Description. ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalyzeFile = async (file: File) => {
    setIsLoading(true);
    setJdData(null);
    setPipelineStep("parsing");
    setEngagedCandidates(new Map());
    setShowRankedShortlist(false);
    try {
      const formData = new FormData();
      formData.append("file", file);
      
      const res = await fetch(`/api/upload-jd`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorPayload = await res.json().catch(() => null);
        throw new Error(errorPayload?.detail || "Failed to parse PDF JD");
      }

      const data: JDData = await res.json();
      setJdData(data);
      setCandidates(null);
      await handleFindMatches(data);
    } catch (error) {
      console.error(error);
      setPipelineStep("idle");
      const errorMessage = error instanceof Error ? error.message : "Unknown PDF parsing error";
      alert(`Failed to analyze the PDF. ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFindMatches = async (dataToMatch: JDData) => {
    if (!dataToMatch) return;
    setIsMatching(true);
    setPipelineStep("matching");
    try {
      const res = await fetch(`/api/match-candidates`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ jd_data: dataToMatch }),
      });

      if (!res.ok) {
        const errorPayload = await res.json().catch(() => null);
        throw new Error(errorPayload?.detail || "Failed to match candidates");
      }

      const data = await res.json();
      setCandidates(data.candidates);
      setPipelineStep("matching"); // Stay on matching step until engagement begins
    } catch (error) {
      console.error(error);
      const errorMessage = error instanceof Error ? error.message : "Unknown matching error";
      alert(`Failed to find matches. ${errorMessage}`);
    } finally {
      setIsMatching(false);
    }
  };

  const handleEngage = (candidate: Candidate) => {
    setSelectedCandidate(candidate);
    setIsModalOpen(true);
  };

  const handleEngagementComplete = useCallback((candidateId: string, result: {
    interest_score: number;
    final_score: number;
    chat_logs: { sender: string; message: string }[];
  }) => {
    if (!candidates) return;
    const candidate = candidates.find(c => c.id === candidateId);
    if (!candidate) return;

    setEngagedCandidates(prev => {
      const newMap = new Map(prev);
      newMap.set(candidateId, {
        ...candidate,
        interest_score: result.interest_score,
        final_score: result.final_score,
        chat_logs: result.chat_logs,
      });
      return newMap;
    });
  }, [candidates]);

  const handleEngageAll = async () => {
    if (!candidates || !jdData) return;

    const pendingCandidates = candidates.filter((candidate) => !engagedCandidates.has(candidate.id));
    if (pendingCandidates.length === 0) {
      setPipelineStep("ranked");
      setShowRankedShortlist(true);
      return;
    }

    setIsEngagingAll(true);
    setPipelineStep("engaging");
    setEngageProgress({ current: 0, total: pendingCandidates.length });

    for (let i = 0; i < pendingCandidates.length; i++) {
      const candidate = pendingCandidates[i];
      setEngageProgress({ current: i + 1, total: pendingCandidates.length });

      try {
        const res = await fetch(`/api/simulate-interest`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ candidate, jd_data: jdData }),
        });

        if (!res.ok) throw new Error("Failed to simulate");
        const data = await res.json();

        setEngagedCandidates(prev => {
          const newMap = new Map(prev);
          newMap.set(candidate.id, {
            ...candidate,
            interest_score: data.interest_score,
            final_score: data.final_score,
            chat_logs: data.chat_logs,
          });
          return newMap;
        });
      } catch (err) {
        console.error(`Failed to engage ${candidate.name}:`, err);
      }
    }

    setIsEngagingAll(false);
    setPipelineStep("ranked");
    setShowRankedShortlist(true);
  };

  // Ranked shortlist view
  if (showRankedShortlist && engagedCandidates.size > 0 && jdData) {
    return (
      <div className="relative z-10 w-full min-h-screen pt-[120px] pb-24 px-6 flex flex-col items-center">
        <PipelineSteps currentStep="ranked" />

        {/* Dashboard Header */}
        <div className="w-full max-w-[1400px] flex items-center justify-between mb-8">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-[#5AE14C]" />
            ScoutIQ Results
          </h2>
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setShowRankedShortlist(false)}
              className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors text-sm font-medium border border-white/10"
            >
              ← Back to Candidates
            </button>
            <button 
              onClick={() => { setJdData(null); setCandidates(null); setEngagedCandidates(new Map()); setShowRankedShortlist(false); setPipelineStep("idle"); }}
              className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors text-sm font-medium border border-white/10"
            >
              New Search
            </button>
          </div>
        </div>

        <RankedShortlist candidates={Array.from(engagedCandidates.values())} />
      </div>
    );
  }

  // Dashboard view (after JD parsed)
  if (jdData) {
    return (
      <div className="relative z-10 w-full min-h-screen pt-[120px] pb-24 px-6 flex flex-col items-center">
        <PipelineSteps currentStep={pipelineStep} />

        {/* Dashboard Header */}
        <div className="w-full max-w-[1400px] flex items-center justify-between mb-8">
           <h2 className="text-2xl font-bold text-white flex items-center gap-2">
             <Sparkles className="w-6 h-6 text-[#5AE14C]" />
             Candidate Discovery Dashboard
           </h2>
           <div className="flex items-center gap-3">
             {/* Primary Action Button */}
             {candidates && candidates.length > 0 && (
               remainingToEngage > 0 ? (
                 <button
                   onClick={handleEngageAll}
                   disabled={isEngagingAll}
                   className="flex items-center gap-2 px-5 py-2.5 bg-[#5AE14C] text-black font-semibold rounded-xl hover:bg-[#4DC93F] transition-all shadow-[0_0_20px_rgba(90,225,76,0.3)] hover:shadow-[0_0_30px_rgba(90,225,76,0.5)] disabled:opacity-50 disabled:cursor-not-allowed group"
                 >
                   {isEngagingAll ? (
                     <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin"></div>
                   ) : (
                     <Users className="w-4 h-4 transition-transform group-hover:scale-110" />
                   )}
                   {isEngagingAll 
                     ? `Engaging ${engageProgress.current}/${engageProgress.total}...` 
                     : engagedCandidates.size > 0 
                       ? `Engage Remaining (${remainingToEngage})`
                       : "Engage All & Rank"
                   }
                 </button>
               ) : (
                 <button
                   onClick={() => { setPipelineStep("ranked"); setShowRankedShortlist(true); }}
                   className="flex items-center gap-2 px-5 py-2.5 bg-[#5AE14C] text-black font-semibold rounded-xl hover:bg-[#4DC93F] transition-all shadow-[0_0_20px_rgba(90,225,76,0.3)] hover:shadow-[0_0_30px_rgba(90,225,76,0.5)]"
                 >
                   <Sparkles className="w-4 h-4" />
                   View Ranked Shortlist
                 </button>
               )
             )}

             {/* Secondary Shortlist Link (Only if some are engaged but not all) */}
             {engagedCandidates.size > 0 && remainingToEngage > 0 && !isEngagingAll && (
               <button
                 onClick={() => { setPipelineStep("ranked"); setShowRankedShortlist(true); }}
                 className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors text-sm font-medium border border-white/10"
               >
                 Partial Shortlist ({engagedCandidates.size})
               </button>
             )}
             <button 
               onClick={() => { setJdData(null); setCandidates(null); setEngagedCandidates(new Map()); setShowRankedShortlist(false); setPipelineStep("idle"); }}
               className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors text-sm font-medium border border-white/10"
             >
               New Search
             </button>
           </div>
        </div>

        {/* Engage All Progress */}
        {isEngagingAll && (
          <div className="w-full max-w-[1400px] mb-6">
            <div className="glassmorphism rounded-[18px] border border-[#5AE14C]/20 p-5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-semibold text-white flex items-center gap-2">
                  <Users className="w-4 h-4 text-[#5AE14C]" />
                  Engaging candidates via AI outreach...
                </span>
                <span className="text-sm font-bold text-[#5AE14C]">
                  {engageProgress.current}/{engageProgress.total}
                </span>
              </div>
              <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-[#5AE14C] transition-all duration-500 ease-out shadow-[0_0_10px_rgba(90,225,76,0.6)]"
                  style={{ width: `${(engageProgress.current / Math.max(engageProgress.total, 1)) * 100}%` }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Dashboard Grid */}
        <div className="w-full max-w-[1400px] grid grid-cols-1 xl:grid-cols-[400px_1fr] gap-8 items-start">
           {/* Left Sidebar: JD Summary */}
           <div className="sticky top-24">
             <JDResults data={jdData} />
           </div>

           {/* Right Main Content: Candidates */}
           <div>
              {isMatching ? (
                <div className="flex flex-col items-center justify-center h-64 gap-4 glassmorphism rounded-[24px] border border-white/10">
                  <div className="w-10 h-10 border-4 border-[#5AE14C] border-t-transparent rounded-full animate-spin"></div>
                  <p className="text-white/60 font-medium animate-pulse">Running Matching Engine...</p>
                </div>
              ) : candidates ? (
                <CandidateList 
                  candidates={candidates} 
                  onEngage={handleEngage} 
                  engagedIds={new Set(engagedCandidates.keys())}
                />
              ) : null}
           </div>
        </div>

        <EngagementModal 
          isOpen={isModalOpen} 
          onClose={() => setIsModalOpen(false)} 
          candidate={selectedCandidate} 
          jdData={jdData}
          onEngagementComplete={handleEngagementComplete}
        />
      </div>
    );
  }

  // Landing page
  return (
    <div className="relative z-10 w-full min-h-screen pt-[160px] pb-24 px-6 flex flex-col items-center justify-center -translate-y-8">
      
      {/* Badges */}
      <div className="flex items-center gap-3 mb-8 bg-white/5 backdrop-blur-md border border-white/10 rounded-full p-1 pr-4 shadow-[0_4px_24px_rgba(0,0,0,0.4)]">
        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-white/15 rounded-full text-xs font-semibold text-white tracking-wide">
          <Zap className="w-3.5 h-3.5 text-[#5AE14C] fill-[#5AE14C]" />
          New
        </div>
        <span className="text-sm font-medium text-white/90 flex items-center gap-2">
          AI Hiring Assistant Live
          <Sparkles className="w-3.5 h-3.5 text-white/70" />
        </span>
      </div>

      {/* Main Headline */}
      <h1 className="font-fustat font-bold text-[56px] md:text-[72px] leading-[1.05] tracking-tight text-white text-center drop-shadow-lg max-w-[900px] mb-6">
        Hire Top Talent Faster<br />With AI Precision
      </h1>

      {/* Subtitle */}
      <p className="font-fustat font-medium text-[18px] md:text-[20px] leading-relaxed text-[rgba(255,255,255,0.82)] text-center max-w-[760px] mb-12 drop-shadow-md">
        Paste a job description, instantly discover qualified candidates, assess real interest, and receive a ranked shortlist your recruiter can act on immediately.
      </p>

      {/* Interactive Phase 0 Card */}
      <JDInputCard onAnalyzeText={handleAnalyzeText} onAnalyzeFile={handleAnalyzeFile} isLoading={isLoading} />

      {/* Feature Cards */}
      <div className="mt-16 w-full flex flex-col items-center">
        <div className="max-w-[1000px] w-full">
          <FeatureCards />
        </div>
      </div>

      {/* Trust Section */}
      <div className="mt-20 flex items-center justify-center gap-4 text-[13px] font-semibold tracking-widest text-[#d1d1d1]/60 uppercase">
        <span>Used by modern recruiters</span>
        <span className="w-1.5 h-1.5 rounded-full bg-[#d1d1d1]/30"></span>
        <span>AI Powered</span>
        <span className="w-1.5 h-1.5 rounded-full bg-[#d1d1d1]/30"></span>
        <span>Instant Shortlisting</span>
      </div>
    </div>
  );
}
