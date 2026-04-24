"use client";

import { ChevronDown } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

export function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 px-[120px] py-[18px] backdrop-blur-md bg-black/10 border-b border-white/5">
      <div className="max-w-[1440px] mx-auto flex items-center justify-between">
        <div className="flex items-center">
          <Link 
            href="/" 
            className="font-schibsted font-semibold text-2xl tracking-tight text-white hover:opacity-80 transition-opacity"
          >
            ScoutIQ
          </Link>
        </div>

        <div className="hidden md:flex items-center gap-8">
          <Link href="#" className="text-[16px] font-medium text-white/90 hover:text-white transition-colors">
            Platform
          </Link>
          <div className="flex items-center gap-1 cursor-pointer group">
            <span className="text-[16px] font-medium text-white/90 group-hover:text-white transition-colors">
              Features
            </span>
            <ChevronDown className="w-4 h-4 text-white/70 group-hover:text-white transition-colors" />
          </div>
          <Link href="#" className="text-[16px] font-medium text-white/90 hover:text-white transition-colors">
            Candidates
          </Link>
          <Link href="#" className="text-[16px] font-medium text-white/90 hover:text-white transition-colors">
            Analytics
          </Link>
          <Link href="#" className="text-[16px] font-medium text-white/90 hover:text-white transition-colors">
            Contact
          </Link>
        </div>

        <div className="flex items-center gap-4">
          <button className="px-5 py-2 text-[15px] font-medium text-white border border-white/20 rounded-full hover:bg-white/10 transition-colors">
            Sign Up
          </button>
          <button className="px-5 py-2 text-[15px] font-medium text-black bg-white rounded-full shadow-[0_0_20px_rgba(255,255,255,0.3)] hover:shadow-[0_0_25px_rgba(255,255,255,0.5)] transition-all transform hover:scale-[1.02]">
            Launch Dashboard
          </button>
        </div>
      </div>
    </nav>
  );
}
