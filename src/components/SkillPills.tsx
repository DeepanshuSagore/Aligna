import { cn } from "@/lib/utils";

interface SkillPillsProps {
  skills: string[];
  type: "must-have" | "good-to-have";
}

export function SkillPills({ skills, type }: SkillPillsProps) {
  if (!skills || skills.length === 0) {
    return <span className="text-sm text-white/50 italic">None specified</span>;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {skills.map((skill, index) => (
        <span
          key={index}
          className={cn(
            "px-3 py-1.5 text-sm font-medium rounded-full border backdrop-blur-md transition-all duration-300 hover:scale-105",
            type === "must-have"
              ? "bg-[#5AE14C]/10 text-[#5AE14C] border-[#5AE14C]/20 shadow-[0_0_10px_rgba(90,225,76,0.1)]"
              : "bg-white/5 text-white/80 border-white/10 hover:bg-white/10"
          )}
        >
          {skill}
        </span>
      ))}
    </div>
  );
}
