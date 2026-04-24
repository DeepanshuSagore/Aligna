"use client";

import { Sparkles, Zap } from "lucide-react";
import { JDInputCard } from "./JDInputCard";
import { FeatureCards } from "./FeatureCards";

export function Hero() {
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
      <JDInputCard />

      {/* Phase 0 Result Preview Panel Placeholder */}
      <div className="mt-16 w-full max-w-[1000px]">
        <FeatureCards />
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
