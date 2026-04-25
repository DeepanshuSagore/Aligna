"use client";

import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type PipelineStep = "idle" | "parsing" | "matching" | "engaging" | "ranked";

interface PipelineStepsProps {
  currentStep: PipelineStep;
}

const steps = [
  { id: "parsing", label: "Parse JD", description: "Analyzing requirements" },
  { id: "matching", label: "Match Candidates", description: "Scoring profiles" },
  { id: "engaging", label: "Engage & Assess", description: "Simulating outreach" },
  { id: "ranked", label: "Ranked Shortlist", description: "Final output ready" },
];

const stepOrder: PipelineStep[] = ["parsing", "matching", "engaging", "ranked"];

function getStepStatus(stepId: string, currentStep: PipelineStep): "complete" | "active" | "pending" {
  const currentIndex = stepOrder.indexOf(currentStep);
  const stepIndex = stepOrder.indexOf(stepId as PipelineStep);

  if (currentStep === "idle") return "pending";
  if (stepIndex < currentIndex) return "complete";
  if (stepIndex === currentIndex) return "active";
  return "pending";
}

export function PipelineSteps({ currentStep }: PipelineStepsProps) {
  if (currentStep === "idle") return null;

  return (
    <div className="w-full max-w-[800px] mx-auto mb-10 animate-in fade-in slide-in-from-top-4 duration-500">
      <div className="glassmorphism rounded-[20px] border border-white/10 p-6 shadow-[0_8px_30px_rgba(0,0,0,0.3)]">
        <div className="flex items-center justify-between relative">
          {/* Connector line */}
          <div className="absolute top-5 left-[10%] right-[10%] h-[2px] bg-white/10 z-0" />
          <div
            className="absolute top-5 left-[10%] h-[2px] bg-[#5AE14C] z-[1] transition-all duration-700 ease-out"
            style={{
              width: `${Math.max(0, (stepOrder.indexOf(currentStep) / (steps.length - 1)) * 80)}%`,
            }}
          />

          {steps.map((step) => {
            const status = getStepStatus(step.id, currentStep);
            return (
              <div
                key={step.id}
                className="relative z-10 flex flex-col items-center gap-2 min-w-[100px]"
              >
                <div
                  className={cn(
                    "w-10 h-10 rounded-full flex items-center justify-center transition-all duration-500 border-2",
                    status === "complete"
                      ? "bg-[#5AE14C] border-[#5AE14C] shadow-[0_0_15px_rgba(90,225,76,0.4)]"
                      : status === "active"
                      ? "bg-[#5AE14C]/20 border-[#5AE14C] shadow-[0_0_15px_rgba(90,225,76,0.3)]"
                      : "bg-white/5 border-white/20"
                  )}
                >
                  {status === "complete" ? (
                    <CheckCircle2 className="w-5 h-5 text-black" />
                  ) : status === "active" ? (
                    <Loader2 className="w-5 h-5 text-[#5AE14C] animate-spin" />
                  ) : (
                    <Circle className="w-5 h-5 text-white/30" />
                  )}
                </div>
                <span
                  className={cn(
                    "text-xs font-semibold tracking-wide text-center transition-colors",
                    status === "complete"
                      ? "text-[#5AE14C]"
                      : status === "active"
                      ? "text-white"
                      : "text-white/40"
                  )}
                >
                  {step.label}
                </span>
                <span
                  className={cn(
                    "text-[10px] text-center transition-colors hidden sm:block",
                    status === "active" ? "text-white/60" : "text-white/30"
                  )}
                >
                  {step.description}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
