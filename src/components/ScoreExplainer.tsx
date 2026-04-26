import { AlertTriangle, BarChart3, CheckCircle2 } from "lucide-react";

export interface ScoreCriterionBreakdown {
  key: string;
  label: string;
  weight: number;
  evaluated: boolean;
  achieved_points: number;
  achieved_percent: number;
  contribution_percent: number;
  detail: string;
}

export interface ScoreBreakdown {
  base_score: number;
  final_score: number;
  penalty_multiplier: number;
  criteria: ScoreCriterionBreakdown[];
  penalties: string[];
}

interface ScoreExplainerProps {
  scoreBreakdown?: ScoreBreakdown | null;
  matchScore: number;
}

function getProgressColor(score: number) {
  if (score >= 75) return "bg-[#5AE14C]";
  if (score >= 40) return "bg-[#FACC15]";
  return "bg-[#F87171]";
}

export function ScoreExplainer({ scoreBreakdown, matchScore }: ScoreExplainerProps) {
  if (!scoreBreakdown) {
    return (
      <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-white/65">
        Detailed criterion-level scoring is not available for this candidate yet.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <p className="flex items-center gap-2 text-sm font-semibold text-white">
          <BarChart3 className="h-4 w-4 text-[#5AE14C]" />
          Score Explainer
        </p>
        <div className="flex flex-wrap items-center gap-2 text-xs text-white/70">
          <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
            Base: {scoreBreakdown.base_score}
          </span>
          <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
            Penalty Multiplier: {scoreBreakdown.penalty_multiplier.toFixed(2)}x
          </span>
          <span className="rounded-full border border-[#5AE14C]/30 bg-[#5AE14C]/10 px-2.5 py-1 font-semibold text-[#5AE14C]">
            Final Match: {scoreBreakdown.final_score} ({matchScore})
          </span>
        </div>
      </div>

      <div className="space-y-3">
        {scoreBreakdown.criteria.map((criterion) => (
          <div key={criterion.key} className="rounded-lg border border-white/10 bg-black/20 p-3">
            <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-white">{criterion.label}</p>
                {!criterion.evaluated && (
                  <span className="rounded-md border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] uppercase tracking-wider text-white/55">
                    Not in JD
                  </span>
                )}
              </div>
              <p className="text-xs text-white/65">
                {criterion.evaluated
                  ? `${criterion.achieved_percent}% of criterion • ${criterion.achieved_points.toFixed(1)}/${criterion.weight.toFixed(0)} pts • ${criterion.contribution_percent}% total`
                  : "Not applicable"}
              </p>
            </div>

            <div className="h-2 overflow-hidden rounded-full bg-white/10">
              <div
                className={`h-full transition-all duration-500 ${getProgressColor(criterion.achieved_percent)}`}
                style={{ width: `${criterion.evaluated ? criterion.achieved_percent : 0}%` }}
              />
            </div>

            <p className="mt-2 text-xs text-white/60">{criterion.detail}</p>
          </div>
        ))}
      </div>

      {scoreBreakdown.penalties.length > 0 ? (
        <div className="mt-4 rounded-lg border border-amber-400/25 bg-amber-500/10 p-3">
          <p className="mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-amber-200">
            <AlertTriangle className="h-3.5 w-3.5" />
            Penalties Applied
          </p>
          <ul className="space-y-1 text-xs text-amber-100/90">
            {scoreBreakdown.penalties.map((penalty) => (
              <li key={penalty}>{penalty}</li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="mt-4 rounded-lg border border-[#5AE14C]/25 bg-[#5AE14C]/10 p-3 text-xs text-[#D8FFD1]">
          <p className="flex items-center gap-2 font-semibold uppercase tracking-wider">
            <CheckCircle2 className="h-3.5 w-3.5" />
            No Penalty Applied
          </p>
        </div>
      )}
    </div>
  );
}
