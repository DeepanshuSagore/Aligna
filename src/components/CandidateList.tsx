"use client";

import { UserCircle2, MapPin, Briefcase, ChevronRight } from "lucide-react";
import { SkillPills } from "./SkillPills";

export interface Candidate {
  id: string;
  name: string;
  role: string;
  skills: string[];
  years_experience: parseInt;
  city: string;
  remote_preference: string;
  expected_salary: string;
  education: string;
  last_company: string;
  open_to_work: boolean;
  match_score: number;
  match_reason: string;
}

interface CandidateListProps {
  candidates: Candidate[];
  onEngage: (candidate: Candidate) => void;
}

export function CandidateList({ candidates, onEngage }: CandidateListProps) {
  if (!candidates || candidates.length === 0) return null;

  return (
    <div className="w-full flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-8 duration-700 pb-24">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-3xl font-fustat font-bold text-white drop-shadow-md">Top Matches</h2>
        <span className="text-white/60 text-sm font-medium">{candidates.length} candidates found</span>
      </div>

      <div className="flex flex-col gap-4">
        {candidates.map((candidate, index) => (
          <div 
            key={candidate.id}
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
            </div>

            {/* Actions */}
            <div className="flex-shrink-0 w-full md:w-auto mt-4 md:mt-0 flex flex-col items-center justify-center">
              <button 
                onClick={() => onEngage(candidate)}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white transition-colors group-hover:bg-white group-hover:text-black group-hover:border-transparent"
              >
                <span>Engage</span>
                <ChevronRight className="w-4 h-4" />
              </button>
              <span className="text-[10px] text-white/50 mt-2 uppercase tracking-widest hidden md:block text-center">
                AI Outreach
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
