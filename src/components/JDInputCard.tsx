"use client";

import { useState, useRef } from "react";
import { ArrowRight, FileText, Sparkles, X, Loader2, UploadCloud } from "lucide-react";
import { cn } from "@/lib/utils";

interface JDInputCardProps {
  onAnalyzeText: (jdText: string) => Promise<void>;
  onAnalyzeFile: (file: File) => Promise<void>;
  isLoading: boolean;
}

const JD_SAMPLES = [
  "Looking for a Senior Frontend Engineer with 4+ years of experience in React, Next.js, and TypeScript. Must have a strong eye for UI/UX and be comfortable working in a fast-paced environment.",
  "We are hiring a Backend Engineer (Node.js) with 3-6 years of experience building scalable APIs, working with PostgreSQL, and deploying services on AWS. Experience with microservices and observability is preferred.",
  "Seeking a Data Analyst with 2+ years of experience in SQL, Python, and dashboarding tools like Looker or Tableau. The role focuses on product metrics, cohort analysis, and executive reporting.",
  "Hiring a Product Designer with 3+ years of SaaS experience. Must be strong in end-to-end design, prototyping in Figma, and collaborating closely with PMs and engineers to ship polished user experiences.",
  "We need a Full-Stack Engineer with 4+ years in React, Node.js, and MongoDB. You will own features end-to-end, collaborate with product, and improve performance, reliability, and developer experience.",
  "Hiring a DevOps Engineer with hands-on experience in Kubernetes, Terraform, and CI/CD pipelines. You will help scale our AWS infrastructure, enforce security best practices, and reduce deployment lead time.",
  "Looking for a QA Automation Engineer with 3+ years of experience in Playwright or Cypress, API testing, and test strategy. Experience with flaky test reduction and CI integration is a big plus.",
  "Seeking a Mobile Engineer (React Native) with 3-5 years of app development experience. Must be comfortable with performance profiling, native module integration, and shipping to both iOS and Android stores.",
  "We are hiring a Machine Learning Engineer with strong Python skills and experience deploying LLM-powered features. Familiarity with vector databases, prompt optimization, and evaluation frameworks is required.",
  "Looking for a Technical Program Manager with experience leading cross-functional product launches. The role requires strong stakeholder communication, dependency management, and data-driven execution.",
];

const shuffleArray = <T,>(items: T[]): T[] => {
  const shuffled = [...items];
  for (let i = shuffled.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
};

export function JDInputCard({ onAnalyzeText, onAnalyzeFile, isLoading }: JDInputCardProps) {
  const [jdText, setJdText] = useState("");
  const [error, setError] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [randomizedSamples] = useState(() => shuffleArray(JD_SAMPLES));
  const [sampleIndex, setSampleIndex] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleAnalyzeClick = async () => {
    if (selectedFile) {
      setError("");
      await onAnalyzeFile(selectedFile);
      return;
    }
    if (!jdText.trim()) {
      setError("Please paste a job description or upload a PDF.");
      return;
    }
    setError("");
    await onAnalyzeText(jdText);
  };

  const handleClear = () => {
    setJdText("");
    setSelectedFile(null);
    setError("");
    if (fileInputRef.current) {
        fileInputRef.current.value = "";
    }
  };

  const handleSample = () => {
    setJdText(randomizedSamples[sampleIndex]);
    setSampleIndex((prev) => (prev + 1) % randomizedSamples.length);
    setSelectedFile(null);
    setError("");
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.type === "application/pdf" || file.name.endsWith(".pdf")) {
        setSelectedFile(file);
        setJdText("");
        setError("");
      } else {
        setError("Only PDF files are supported right now.");
      }
    }
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (file.type === "application/pdf" || file.name.endsWith(".pdf")) {
        setSelectedFile(file);
        setJdText("");
        setError("");
      } else {
        setError("Only PDF files are supported right now.");
      }
    }
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
          <span>Powered by Aligna-AI</span>
        </div>
      </div>

      {/* Main Drag-and-Drop / Textarea */}
      <div className="p-6 pb-4">
        <div 
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            className={cn(
                "relative w-full rounded-[16px] overflow-hidden transition-all duration-300 border-2", 
                isDragging ? "border-[#5AE14C] bg-[#5AE14C]/10 scale-[1.01] shadow-[0_0_30px_rgba(90,225,76,0.2)]" : 
                error ? "border-red-500 bg-gray-100" : "border-transparent bg-gray-100"
            )}
        >
          {selectedFile ? (
              <div className="w-full h-[180px] md:h-[220px] flex flex-col items-center justify-center gap-4 bg-white/5">
                  <div className="w-16 h-16 rounded-2xl bg-blue-50 flex items-center justify-center shadow-inner">
                      <FileText className="w-8 h-8 text-blue-500" />
                  </div>
                  <div className="text-center">
                      <p className="text-lg font-bold text-gray-800">{selectedFile.name}</p>
                      <p className="text-sm text-gray-500 font-medium">PDF Ready for Analysis</p>
                  </div>
                  {!isLoading && (
                    <button 
                    onClick={handleClear}
                    className="absolute top-4 right-4 p-1.5 bg-gray-100 rounded-full text-gray-500 hover:bg-gray-200 hover:text-gray-700 transition-colors shadow-sm"
                    >
                    <X className="w-4 h-4" />
                    </button>
                  )}
              </div>
          ) : (
            <>
                <textarea
                    value={jdText}
                    onChange={(e) => {
                    setJdText(e.target.value);
                    if (error) setError("");
                    }}
                    disabled={isLoading}
                    placeholder="Paste Job Description here, or drag and drop a PDF file..."
                    className={cn(
                        "w-full h-[180px] md:h-[220px] p-6 text-black placeholder:text-gray-600 bg-transparent resize-none outline-none font-inter text-[16px] leading-[1.6] disabled:opacity-70 disabled:cursor-not-allowed",
                        isDragging && "opacity-30"
                    )}
                />
                {isDragging && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                        <UploadCloud className="w-12 h-12 text-[#5AE14C] mb-2 animate-bounce" />
                        <span className="text-xl font-bold text-[#5AE14C]">Drop PDF Here</span>
                    </div>
                )}
                {jdText && !isLoading && (
                    <button 
                    onClick={handleClear}
                    className="absolute top-4 right-4 p-1.5 bg-gray-100 rounded-full text-gray-500 hover:bg-gray-200 hover:text-gray-700 transition-colors shadow-sm"
                    >
                    <X className="w-4 h-4" />
                    </button>
                )}
            </>
          )}
        </div>
        {error && (
          <p className="text-red-400 text-sm mt-2 ml-1 animate-in fade-in slide-in-from-top-1">{error}</p>
        )}
      </div>

      {/* Bottom Action Row */}
      <div className="px-6 py-5 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-white/5">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <input 
            type="file" 
            accept=".pdf" 
            className="hidden" 
            ref={fileInputRef} 
            onChange={onFileChange} 
          />
          <button 
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading}
            className="flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white/80 border border-white/20 rounded-full hover:bg-white/10 hover:text-white transition-all w-full sm:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <UploadCloud className="w-4 h-4" />
            Upload PDF
          </button>
          <button 
            onClick={handleSample}
            disabled={isLoading || selectedFile !== null}
            className="flex items-center justify-center px-4 py-2 text-sm font-medium text-white/80 border border-white/20 rounded-full hover:bg-white/10 hover:text-white transition-all w-full sm:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Use Sample
          </button>
        </div>

        <button 
          onClick={handleAnalyzeClick}
          disabled={(!jdText.trim() && !selectedFile) || isLoading}
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
