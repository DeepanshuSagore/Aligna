"use client";

import { useState } from "react";
import { ChevronDown, Menu, X } from "lucide-react";
import Link from "next/link";

const navItems = [
  { label: "Platform", href: "#" },
  { label: "Candidates", href: "#" },
  { label: "Analytics", href: "#" },
  { label: "Contact", href: "#" },
];

export function Navbar() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 px-4 md:px-8 lg:px-12 py-4 backdrop-blur-md bg-black/10 border-b border-white/5">
      <div className="max-w-[1440px] mx-auto flex items-center justify-between">
        <div className="flex items-center">
          <Link 
            href="/" 
            className="font-schibsted font-semibold text-2xl tracking-tight text-white hover:opacity-80 transition-opacity"
          >
            ScoutIQ
          </Link>
        </div>

        <div className="hidden lg:flex items-center gap-8">
          {navItems.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className="text-[16px] font-medium text-white/90 hover:text-white transition-colors"
            >
              {item.label}
            </Link>
          ))}
          <div className="flex items-center gap-1 cursor-pointer group">
            <span className="text-[16px] font-medium text-white/90 group-hover:text-white transition-colors">
              Features
            </span>
            <ChevronDown className="w-4 h-4 text-white/70 group-hover:text-white transition-colors" />
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-3">
          <button className="px-5 py-2 text-[15px] font-medium text-white border border-white/20 rounded-full hover:bg-white/10 transition-colors">
            Sign Up
          </button>
          <button className="px-5 py-2 text-[15px] font-medium text-black bg-white rounded-full shadow-[0_0_20px_rgba(255,255,255,0.3)] hover:shadow-[0_0_25px_rgba(255,255,255,0.5)] transition-all transform hover:scale-[1.02]">
            Launch Dashboard
          </button>
        </div>

        <button
          onClick={() => setIsMobileMenuOpen((prev) => !prev)}
          className="sm:hidden p-2 rounded-lg border border-white/20 text-white hover:bg-white/10 transition-colors"
          aria-label="Toggle navigation menu"
        >
          {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {isMobileMenuOpen && (
        <div className="sm:hidden max-w-[1440px] mx-auto mt-4 p-4 rounded-2xl glassmorphism border border-white/10">
          <div className="flex flex-col gap-3">
            <Link href="#" className="text-[15px] font-medium text-white/90 hover:text-white transition-colors">Platform</Link>
            <Link href="#" className="text-[15px] font-medium text-white/90 hover:text-white transition-colors">Features</Link>
            {navItems.slice(1).map((item) => (
              <Link
                key={item.label}
                href={item.href}
                className="text-[15px] font-medium text-white/90 hover:text-white transition-colors"
              >
                {item.label}
              </Link>
            ))}
          </div>
          <div className="flex flex-col gap-2 mt-4">
            <button className="px-4 py-2 text-[14px] font-medium text-white border border-white/20 rounded-xl hover:bg-white/10 transition-colors">
              Sign Up
            </button>
            <button className="px-4 py-2 text-[14px] font-medium text-black bg-white rounded-xl transition-colors hover:bg-white/90">
              Launch Dashboard
            </button>
          </div>
        </div>
      )}
    </nav>
  );
}
