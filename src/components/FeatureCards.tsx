"use client";

import { BrainCircuit, Users, Target } from "lucide-react";

export function FeatureCards() {
  const cards = [
    {
      icon: <BrainCircuit className="w-5 h-5 text-white" />,
      title: "JD Parsing",
      desc: "Instantly extracts core requirements, seniority, and nice-to-haves from unstructured text.",
    },
    {
      icon: <Users className="w-5 h-5 text-white" />,
      title: "Candidate Matching",
      desc: "Scores resumes semantically against extracted skills to find the perfect fit.",
    },
    {
      icon: <Target className="w-5 h-5 text-white" />,
      title: "Interest Scoring",
      desc: "Predicts candidate responsiveness and calculates real intent to switch roles.",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
      {cards.map((card, i) => (
        <div 
          key={i} 
          className="relative overflow-hidden group rounded-[18px] p-6 glassmorphism transition-all duration-300 hover:bg-white/10 hover:-translate-y-1 hover:shadow-[0_10px_30px_rgba(255,255,255,0.05)] border border-white/5 hover:border-white/20"
        >
          {/* Subtle gradient glow effect on hover */}
          <div className="absolute top-0 right-0 -mr-8 -mt-8 w-32 h-32 rounded-full bg-white/5 blur-3xl group-hover:bg-white/10 transition-colors duration-500"></div>
          
          <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center mb-5 border border-white/10 shadow-inner group-hover:bg-white/20 transition-colors">
            {card.icon}
          </div>
          
          <h3 className="font-schibsted font-semibold text-[17px] text-white mb-2 tracking-wide">
            {card.title}
          </h3>
          
          <p className="font-inter text-[14px] leading-relaxed text-[#d1d1d1]/80 mt-1">
            {card.desc}
          </p>
        </div>
      ))}
    </div>
  );
}
