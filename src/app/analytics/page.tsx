"use client";

import { useEffect, useMemo, useState } from "react";
import { AuroraBackground } from "@/components/ui/AuroraBackground";
import { Navbar } from "@/components/Navbar";
import { Briefcase, ChartColumnBig, Globe2, RefreshCw, Users } from "lucide-react";

interface CountByLabel {
  label: string;
  count: number;
}

interface CandidateStatsResponse {
  source: string;
  total_candidates: number;
  open_to_work_candidates: number;
  remote_friendly_candidates: number;
  average_years_experience: number;
  top_roles: CountByLabel[];
  top_cities: CountByLabel[];
}

function BreakdownSection({
  title,
  rows,
  accentClass,
}: {
  title: string;
  rows: CountByLabel[];
  accentClass: string;
}) {
  const maxValue = useMemo(() => Math.max(...rows.map((row) => row.count), 1), [rows]);

  return (
    <section className="glassmorphism rounded-2xl border border-white/10 p-5">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-white/60">{title}</h2>
      <div className="space-y-3">
        {rows.length === 0 && <p className="text-sm text-white/60">No data available.</p>}

        {rows.map((row) => (
          <div key={`${title}-${row.label}`}>
            <div className="mb-1 flex items-center justify-between gap-3 text-sm text-white/80">
              <span className="truncate">{row.label}</span>
              <span className="font-semibold text-white">{row.count}</span>
            </div>
            <div className="h-2 rounded-full bg-white/10">
              <div
                className={`h-full rounded-full ${accentClass}`}
                style={{ width: `${Math.max(8, (row.count / maxValue) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function AnalyticsPage() {
  const [stats, setStats] = useState<CandidateStatsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchStats = async () => {
    const response = await fetch("/api/candidates/stats", { cache: "no-store" });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || "Failed to load analytics");
    }

    return (await response.json()) as CandidateStatsResponse;
  };

  const handleRefresh = async () => {
    setIsLoading(true);
    setError("");

    try {
      const payload = await fetchStats();
      setStats(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error while loading analytics");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;

    const hydrate = async () => {
      try {
        const payload = await fetchStats();
        if (isMounted) {
          setStats(payload);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Unknown error while loading analytics");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void hydrate();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <main className="relative min-h-screen overflow-x-hidden">
      <AuroraBackground />
      <Navbar />

      <div className="relative z-10 mx-auto w-full max-w-[1400px] px-6 pt-[120px] pb-20">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="font-fustat text-4xl font-bold text-white">Analytics</h1>
            <p className="mt-2 text-white/65">Live overview of the talent pool in ScoutIQ.</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-white/60">
              Source: {stats?.source ?? "-"}
            </span>
            <button
              onClick={() => void handleRefresh()}
              className="inline-flex items-center gap-2 rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-white/10"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
          </div>
        </div>

        {isLoading && (
          <div className="glassmorphism flex h-44 items-center justify-center rounded-2xl border border-white/10">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#5AE14C] border-t-transparent" />
          </div>
        )}

        {!isLoading && error && (
          <div className="rounded-2xl border border-red-400/30 bg-red-500/10 p-6 text-red-100">{error}</div>
        )}

        {!isLoading && !error && stats && (
          <>
            <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="glassmorphism rounded-2xl border border-white/10 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-white/50">Total Candidates</p>
                <p className="mt-3 flex items-center gap-2 text-3xl font-bold text-white">
                  <Users className="h-6 w-6 text-[#5AE14C]" />
                  {stats.total_candidates}
                </p>
              </div>

              <div className="glassmorphism rounded-2xl border border-white/10 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-white/50">Open To Work</p>
                <p className="mt-3 flex items-center gap-2 text-3xl font-bold text-white">
                  <Briefcase className="h-6 w-6 text-blue-300" />
                  {stats.open_to_work_candidates}
                </p>
              </div>

              <div className="glassmorphism rounded-2xl border border-white/10 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-white/50">Remote Friendly</p>
                <p className="mt-3 flex items-center gap-2 text-3xl font-bold text-white">
                  <Globe2 className="h-6 w-6 text-cyan-300" />
                  {stats.remote_friendly_candidates}
                </p>
              </div>

              <div className="glassmorphism rounded-2xl border border-white/10 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-white/50">Avg Experience</p>
                <p className="mt-3 flex items-center gap-2 text-3xl font-bold text-white">
                  <ChartColumnBig className="h-6 w-6 text-yellow-300" />
                  {stats.average_years_experience}y
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <BreakdownSection title="Top Roles" rows={stats.top_roles} accentClass="bg-[#5AE14C]" />
              <BreakdownSection title="Top Cities" rows={stats.top_cities} accentClass="bg-cyan-400" />
            </div>
          </>
        )}
      </div>
    </main>
  );
}
