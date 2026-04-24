"use client";

import { useState } from "react";
import { ArrowRight, FileText, Sparkles, X, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface JDInputCardProps {
  onAnalyze: (jdText: string) => Promise<void>;
  isLoading: boolean;
}

export function JDInputCard({ onAnalyze, isLoading }: JDInputCardProps) {
  const [jdText, setJdText] = useState("");
  const [error, setError] = useState("");

  const handleAnalyzeClick = async () => {
    if (!jdText.trim()) {
      setError("Please enter a job description.");
      return;
    }
    setError("");
    await onAnalyze(jdText);
  };

  const handleClear = () => {
    setJdText("");
    setError("");
  };

  const handleSample = () => {
    setJdText("Looking for a Senior Frontend Engineer with 4+ years of experience in React, Next.js, and TypeScript. Must have a strong eye for UI/UX and be comfortable working in a fast-paced environment.");
    setError("");
  };

  return (
    <div className="w-full max-w-[820px] rounded-[22px] glassmorphism shadow-[0_20px_40px_rgba(0,0,0,0.4)] overflow-hidden flex flex-col transition-all duration-300 hover:shadow-[0_20px_50px_rgba(0,0,0,0.5)] border border-white/10">
      
      {/* Top Status Row */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-white/[0.02]">
        <div className="flex items-center gap-2.5">
          <div className="relative flex items-center justify-center">
            <span className={cn("w-2.5 h-2.5 rounded-full", isLoading ? "bg-yellow-400" : "bg-[#5AE14C] animate-pulse")}></span>
            <span className={cn("absolute w-2.5 h-2.5 rounded-full blur-[4px] opacity-60", isLoading ? "bg-yellow-400 animate-pulse" : "bg-[#5AE14C] animate-pulse")}></span>
          </div>
          <span className="text-sm font-medium text-[#d1d1d1]">
            System Status: {isLoading ? "Parsing Data..." : "Ready"}
          </span>
        </div>
        
        <div className="flex items-center gap-2 text-sm font-medium text-[#d1d1d1]">
          <Sparkles className="w-4 h-4 text-white" />
          <span>Powered by Gemini</span>
        </div>
      </div>

      {/* Main Textarea */}
      <div className="p-6 pb-4">
        <div className={cn("relative w-full rounded-[16px] bg-white overflow-hidden shadow-inner group transition-colors border", error ? "border-red-500" : "border-transparent")}>
          <textarea
            value={jdText}
            onChange={(e) => {
              setJdText(e.target.value);
              if (error) setError("");
            }}
            disabled={isLoading}
            placeholder="Paste Job Description here...&#10;Example:&#10;Need Frontend Developer with React, Next.js, 2+ years experience"
            className="w-full h-[180px] md:h-[220px] p-6 text-black placeholder:text-gray-400 bg-transparent resize-none outline-none font-inter text-[16px] leading-[1.6] disabled:opacity-70 disabled:cursor-not-allowed"
          />
          {jdText && !isLoading && (
            <button 
              onClick={handleClear}
              className="absolute top-4 right-4 p-1.5 bg-gray-100 rounded-full text-gray-500 hover:bg-gray-200 hover:text-gray-700 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
        {error && (
          <p className="text-red-400 text-sm mt-2 ml-1 animate-in fade-in slide-in-from-top-1">{error}</p>
        )}
      </div>

      {/* Bottom Action Row */}
      <div className="px-6 py-5 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-white/5">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button 
            disabled={isLoading}
            className="flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white/80 border border-white/20 rounded-full hover:bg-white/10 hover:text-white transition-all w-full sm:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <FileText className="w-4 h-4" />
            Upload JD
          </button>
          <button 
            onClick={handleSample}
            disabled={isLoading}
            className="flex items-center justify-center px-4 py-2 text-sm font-medium text-white/80 border border-white/20 rounded-full hover:bg-white/10 hover:text-white transition-all w-full sm:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Use Sample
          </button>
        </div>

        <button 
          onClick={handleAnalyzeClick}
          disabled={!jdText.trim() || isLoading}
          className="group relative flex items-center justify-center gap-2 px-6 py-3.5 bg-black text-white font-semibold rounded-xl w-full sm:w-auto overflow-hidden transition-all shadow-[0_0_20px_rgba(255,255,255,0.15)] hover:shadow-[0_0_25px_rgba(255,255,255,0.3)] disabled:opacity-50 disabled:cursor-not-allowed hover:-translate-y-0.5"
        >
          <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-[100%] group-hover:animate-[shimmer_1.5s_infinite]"></div>
          <span className="relative z-10 flex items-center gap-2">
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Parsing Job Description...
              </>
            ) : (
              "Analyze Candidates"
            )}
          </span>
          {!isLoading && <ArrowRight className="w-4 h-4 relative z-10 transition-transform group-hover:translate-x-1" />}
        </button>
      </div>
    </div>
  );
}
