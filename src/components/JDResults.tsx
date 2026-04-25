import { Briefcase, MapPin, Star, Clock, Target, CheckCircle2 } from "lucide-react";
import { SkillPills } from "./SkillPills";

export interface JDData {
  role: string;
  experience_required: string;
  must_have_skills: string[];
  good_to_have_skills: string[];
  location: string;
  seniority: string;
  summary: string;
}

interface JDResultsProps {
  data: JDData;
  onFindCandidates?: () => void;
  isMatching?: boolean;
}

export function JDResults({ data, onFindCandidates, isMatching }: JDResultsProps) {
  return (
    <div className="w-full max-w-[1000px] flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
      
      {/* Top 4 Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <InfoCard icon={<Briefcase className="w-5 h-5" />} label="Role" value={data.role} />
        <InfoCard icon={<Clock className="w-5 h-5" />} label="Experience" value={data.experience_required} />
        <InfoCard icon={<MapPin className="w-5 h-5" />} label="Location" value={data.location} />
        <InfoCard icon={<Star className="w-5 h-5" />} label="Seniority" value={data.seniority} />
      </div>

      {/* Main Details Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        
        {/* Skills Column */}
        <div className="lg:col-span-2 flex flex-col gap-4">
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

      {/* Action Row */}
      {onFindCandidates && (
        <div className="flex justify-center mt-6">
          <button 
            onClick={onFindCandidates}
            disabled={isMatching}
            className="group relative flex items-center justify-center gap-2 px-8 py-4 bg-white text-black font-bold rounded-xl overflow-hidden transition-all shadow-[0_0_20px_rgba(255,255,255,0.4)] hover:shadow-[0_0_30px_rgba(255,255,255,0.6)] disabled:opacity-70 disabled:cursor-not-allowed hover:-translate-y-0.5"
          >
            <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-black/10 to-transparent -translate-x-[100%] group-hover:animate-[shimmer_1.5s_infinite]"></div>
            <span className="relative z-10">
              {isMatching ? "Running Matching Engine..." : "Find Matching Candidates"}
            </span>
            {!isMatching && <CheckCircle2 className="w-5 h-5 relative z-10 transition-transform group-hover:translate-x-1" />}
          </button>
        </div>
      )}

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
