"use client";

import { useState } from "react";
import { ArrowRight, FileText, Sparkles, X } from "lucide-react";
import { cn } from "@/lib/utils";

export function JDInputCard() {
  const [jdText, setJdText] = useState("");

  const handleAnalyze = async () => {
    // later call FastAPI backend
    console.log("Analyzing Job Description:", jdText);
    // Placeholder response logic
    alert("Phase 0: This will call the backend API in the future.");
  };

  const handleClear = () => setJdText("");
  const handleSample = () => setJdText("Looking for a Senior Frontend Engineer with 4+ years of experience in React, Next.js, and TypeScript. Must have a strong eye for UI/UX and be comfortable working in a fast-paced environment.");

  return (
    <div className="w-full max-w-[820px] rounded-[22px] glassmorphism shadow-[0_20px_40px_rgba(0,0,0,0.4)] overflow-hidden flex flex-col transition-all duration-300 hover:shadow-[0_20px_50px_rgba(0,0,0,0.5)] border border-white/10">
      
      {/* Top Status Row */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-white/[0.02]">
        <div className="flex items-center gap-2.5">
          <div className="relative flex items-center justify-center">
            <span className="w-2.5 h-2.5 rounded-full bg-[#5AE14C] animate-pulse"></span>
            <span className="absolute w-2.5 h-2.5 rounded-full bg-[#5AE14C] blur-[4px] opacity-60 animate-pulse"></span>
          </div>
          <span className="text-sm font-medium text-[#d1d1d1]">System Status: Ready</span>
        </div>
        
        <div className="flex items-center gap-2 text-sm font-medium text-[#d1d1d1]">
          <Sparkles className="w-4 h-4 text-white" />
          <span>Powered by Gemini</span>
        </div>
      </div>

      {/* Main Textarea */}
      <div className="p-6 pb-4">
        <div className="relative w-full rounded-[16px] bg-white overflow-hidden shadow-inner group">
          <textarea
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            placeholder="Paste Job Description here...&#10;Example:&#10;Need Frontend Developer with React, Next.js, 2+ years experience"
            className="w-full h-[180px] md:h-[220px] p-6 text-black placeholder:text-gray-400 bg-transparent resize-none outline-none font-inter text-[16px] leading-[1.6]"
          />
          {jdText && (
            <button 
              onClick={handleClear}
              className="absolute top-4 right-4 p-1.5 bg-gray-100 rounded-full text-gray-500 hover:bg-gray-200 hover:text-gray-700 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Bottom Action Row */}
      <div className="px-6 py-5 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-white/5">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button className="flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white/80 border border-white/20 rounded-full hover:bg-white/10 hover:text-white transition-all w-full sm:w-auto">
            <FileText className="w-4 h-4" />
            Upload JD
          </button>
          <button 
            onClick={handleSample}
            className="flex items-center justify-center px-4 py-2 text-sm font-medium text-white/80 border border-white/20 rounded-full hover:bg-white/10 hover:text-white transition-all w-full sm:w-auto"
          >
            Use Sample
          </button>
        </div>

        <button 
          onClick={handleAnalyze}
          disabled={!jdText.trim()}
          className="group relative flex items-center justify-center gap-2 px-6 py-3.5 bg-black text-white font-semibold rounded-xl w-full sm:w-auto overflow-hidden transition-all shadow-[0_0_20px_rgba(255,255,255,0.15)] hover:shadow-[0_0_25px_rgba(255,255,255,0.3)] disabled:opacity-50 disabled:cursor-not-allowed hover:-translate-y-0.5"
        >
          <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-[100%] group-hover:animate-[shimmer_1.5s_infinite]"></div>
          <span className="relative z-10">Analyze Candidates</span>
          <ArrowRight className="w-4 h-4 relative z-10 transition-transform group-hover:translate-x-1" />
        </button>
      </div>
    </div>
  );
}
