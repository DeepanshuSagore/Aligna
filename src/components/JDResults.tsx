import { Briefcase, MapPin, Star, Clock, Target, CheckCircle2, AlertTriangle } from "lucide-react";
import { SkillPills } from "./SkillPills";

export interface JDData {
  role: string;
  experience_required: string;
  must_have_skills: string[];
  good_to_have_skills: string[];
  location: string;
  work_location_preference?: string;
  seniority: string;
  summary: string;
  parse_success?: boolean;
  warning?: string | null;
}

interface JDResultsProps {
  data: JDData;
}

export function JDResults({ data }: JDResultsProps) {
  return (
    <div className="w-full flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-8 duration-700">

      {(data.parse_success === false || data.warning) && (
        <div className="glassmorphism p-5 rounded-[22px] border border-red-500/40 bg-red-500/10 shadow-[0_8px_30px_rgba(239,68,68,0.2)] animate-pulse">
          <div className="flex items-start gap-4">
            <div className="p-2 bg-red-500/20 rounded-full">
              <AlertTriangle className="w-6 h-6 text-red-400" />
            </div>
            <div>
              <p className="text-base font-bold text-red-200 uppercase tracking-tight">JD Parsing Alert</p>
              <p className="text-sm text-red-100/80 leading-relaxed mt-1 font-medium">
                {data.warning || "ALIGNA could not automatically extract all JD fields. Matching quality may be significantly reduced."}
              </p>
              <div className="mt-3 flex items-center gap-2">
                <span className="text-[11px] font-bold px-2 py-0.5 bg-red-500/30 text-red-100 rounded-md border border-red-500/30">
                  ACTION REQUIRED
                </span>
                <p className="text-[11px] text-red-200/70">Verify the extracted skills below before engaging candidates.</p>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Top 4 Summary Cards */}
      <div className="grid grid-cols-2 gap-3">
        <InfoCard icon={<Briefcase className="w-5 h-5" />} label="Role" value={data.role} />
        <InfoCard icon={<Clock className="w-5 h-5" />} label="Experience" value={data.experience_required} />
        <InfoCard icon={<MapPin className="w-5 h-5" />} label="Location" value={data.location} />
        <InfoCard icon={<MapPin className="w-5 h-5" />} label="Work Mode" value={data.work_location_preference || "Not specified"} />
        <InfoCard icon={<Star className="w-5 h-5" />} label="Seniority" value={data.seniority} />
      </div>

      {/* Main Details Section */}
      <div className="flex flex-col gap-4">
        
        {/* Skills Column */}
        <div className="flex flex-col gap-4">
          <div className="glassmorphism p-6 rounded-[22px] border border-white/10 shadow-[0_8px_30px_rgba(0,0,0,0.3)]">
            <div className="flex items-center gap-2 mb-4">
              <Target className="w-5 h-5 text-[#5AE14C]" />
              <h3 className="text-lg font-semibold text-white">Must Have Skills</h3>
            </div>
            <SkillPills skills={data.must_have_skills} type="must-have" />
          </div>

          <div className="glassmorphism p-6 rounded-[22px] border border-white/10 shadow-[0_8px_30px_rgba(0,0,0,0.3)]">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle2 className="w-5 h-5 text-white/70" />
              <h3 className="text-lg font-semibold text-white">Good To Have</h3>
            </div>
            <SkillPills skills={data.good_to_have_skills} type="good-to-have" />
          </div>
        </div>

        {/* Summary Column */}
        <div className="glassmorphism p-6 rounded-[22px] border border-white/10 shadow-[0_8px_30px_rgba(0,0,0,0.3)] h-full">
          <h3 className="text-lg font-semibold text-white mb-4">AI Summary</h3>
          <p className="text-white/80 leading-relaxed text-[15px]">
            {data.summary}
          </p>
        </div>
      </div>
    </div>
  );
}

function InfoCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="glassmorphism p-5 rounded-[20px] border border-white/10 shadow-[0_8px_30px_rgba(0,0,0,0.3)] flex items-start gap-4 transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_15px_40px_rgba(0,0,0,0.4)]">
      <div className="p-3 bg-white/5 rounded-xl text-white/80 border border-white/10">
        {icon}
      </div>
      <div>
        <p className="text-[13px] font-medium text-white/50 uppercase tracking-wider mb-1">{label}</p>
        <p className="text-[16px] font-semibold text-white truncate max-w-[150px]" title={value}>
          {value}
        </p>
      </div>
    </div>
  );
}
