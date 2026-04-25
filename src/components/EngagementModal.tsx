"use client";

import { useEffect, useState } from "react";
import { X, Bot, UserCircle2, Loader2, Target, Award } from "lucide-react";
import { type Candidate } from "./CandidateList";
import { type JDData } from "./JDResults";

interface EngagementModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidate: Candidate | null;
  jdData: JDData | null;
}

interface ChatMessage {
  sender: string;
  message: string;
}

interface SimulationResult {
  chat_logs: ChatMessage[];
  interest_score: number;
  final_score: number;
}

export function EngagementModal({ isOpen, onClose, candidate, jdData }: EngagementModalProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);

  useEffect(() => {
    if (isOpen && candidate && jdData) {
      // Reset state on open
      setResult(null);
      setIsLoading(true);

      const simulate = async () => {
        try {
          const res = await fetch("http://localhost:8000/simulate-interest", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ candidate, jd_data: jdData }),
          });

          if (!res.ok) throw new Error("Failed to simulate");
          const data = await res.json();
          setResult(data);
        } catch (err) {
          console.error(err);
        } finally {
          setIsLoading(false);
        }
      };

      simulate();
    }
  }, [isOpen, candidate, jdData]);

  if (!isOpen || !candidate) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md animate-in fade-in duration-300">
      <div className="relative w-full max-w-2xl bg-[#0f0f13] border border-white/10 rounded-[24px] shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between bg-white/5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center">
              <Bot className="w-5 h-5 text-white/80" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">AI Outreach Simulation</h2>
              <p className="text-xs text-white/50">Engaging {candidate.name}</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-full transition-colors text-white/70"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 flex flex-col">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-64 gap-4">
              <Loader2 className="w-10 h-10 text-white/50 animate-spin" />
              <p className="text-white/60 font-medium animate-pulse">ScoutIQ is chatting with the candidate...</p>
            </div>
          ) : result ? (
            <div className="flex flex-col gap-6">
              
              {/* Score Recap */}
              <div className="grid grid-cols-2 gap-4 mb-2">
                <div className="glassmorphism p-4 rounded-xl border border-white/10 flex flex-col items-center justify-center text-center relative overflow-hidden group">
                  <div className="absolute inset-0 bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <span className="text-white/50 text-xs font-semibold uppercase tracking-wider mb-1 flex items-center gap-1">
                    <Target className="w-3 h-3" /> Interest Score
                  </span>
                  <span className={`text-3xl font-bold mb-2 ${result.interest_score >= 70 ? 'text-[#5AE14C]' : result.interest_score >= 40 ? 'text-[#FACC15]' : 'text-[#F87171]'}`}>
                    {result.interest_score}/100
                  </span>
                  <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-1000 ease-out ${result.interest_score >= 70 ? 'bg-[#5AE14C]' : result.interest_score >= 40 ? 'bg-[#FACC15]' : 'bg-[#F87171]'}`}
                      style={{ width: `${result.interest_score}%` }}
                    ></div>
                  </div>
                </div>
                
                <div className="glassmorphism p-4 rounded-xl border border-[#5AE14C]/30 bg-[#5AE14C]/5 flex flex-col items-center justify-center text-center relative overflow-hidden group">
                  <div className="absolute inset-0 bg-[#5AE14C]/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <span className="text-[#5AE14C]/80 text-xs font-semibold uppercase tracking-wider mb-1 flex items-center gap-1">
                    <Award className="w-3 h-3" /> Final Score
                  </span>
                  <span className="text-3xl font-bold text-[#5AE14C] drop-shadow-[0_0_10px_rgba(90,225,76,0.4)] mb-2">
                    {result.final_score}/100
                  </span>
                  <div className="w-full h-1.5 bg-[#5AE14C]/20 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-[#5AE14C] transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(90,225,76,0.8)]"
                      style={{ width: `${result.final_score}%` }}
                    ></div>
                  </div>
                </div>
              </div>

              {/* Chat Log */}
              <div className="flex flex-col gap-4 mt-2">
                {result.chat_logs.map((msg, i) => {
                  const isScout = msg.sender === "ScoutIQ";
                  return (
                    <div key={i} className={`flex gap-3 ${isScout ? "justify-start" : "justify-end"}`}>
                      {isScout && (
                        <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0 mt-1 border border-blue-500/30">
                          <Bot className="w-4 h-4 text-blue-400" />
                        </div>
                      )}
                      
                      <div className={`max-w-[80%] p-4 rounded-2xl ${
                        isScout 
                          ? "bg-white/10 text-white/90 rounded-tl-sm border border-white/5" 
                          : "bg-blue-600/30 text-white rounded-tr-sm border border-blue-500/30"
                      }`}>
                        <p className="text-xs text-white/40 mb-1 font-medium">{msg.sender}</p>
                        <p className="text-sm leading-relaxed">{msg.message}</p>
                      </div>

                      {!isScout && (
                        <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center flex-shrink-0 mt-1 border border-white/10">
                          <UserCircle2 className="w-4 h-4 text-white/70" />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

            </div>
          ) : (
             <div className="flex flex-col items-center justify-center h-64">
               <p className="text-red-400">Failed to load simulation.</p>
             </div>
          )}
        </div>

        {/* Footer */}
        {result && (
          <div className="px-6 py-4 border-t border-white/10 bg-white/5 flex justify-end">
             <button 
                onClick={onClose}
                className="px-6 py-2 bg-white text-black font-semibold rounded-lg hover:bg-white/90 transition-colors"
             >
                Done
             </button>
          </div>
        )}
      </div>
    </div>
  );
}
