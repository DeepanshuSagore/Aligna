"use client";

import { useEffect, useMemo, useState } from "react";
import { AuroraBackground } from "@/components/ui/AuroraBackground";
import { Navbar } from "@/components/Navbar";
import { Briefcase, Globe2, RefreshCw, Search, Users, ChevronLeft, ChevronRight } from "lucide-react";

interface CandidateRecord {
  id: string;
  name: string;
  role: string;
  skills: string[];
  years_experience: number;
  city: string;
  remote_preference: string;
  work_location_preference?: string;
  open_to_work: boolean;
}

interface CandidatesResponse {
  source: string;
  count: number;
  candidates: CandidateRecord[];
}

const ITEMS_PER_PAGE = 15;

const normalizeSearchText = (value: string) =>
  (value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9+\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const normalizeWorkMode = (value: string) => {
  const text = normalizeSearchText(value);
  if (!text || text === "not specified") return "not-specified";
  if (text.includes("hybrid")) return "hybrid";
  if (text.includes("remote")) return "remote";
  if (text.includes("on site") || text.includes("onsite") || text.includes("office") || text.includes("offline")) return "onsite";
  if (text.includes("any") || text.includes("flexible")) return "flexible";
  return "not-specified";
};

export default function CandidatesPage() {
  const [data, setData] = useState<CandidatesResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [onlyOpenToWork, setOnlyOpenToWork] = useState(false);
  const [workModeFilter, setWorkModeFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);

  const fetchCandidates = async () => {
    const response = await fetch("/api/candidates", { cache: "no-store" });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || "Failed to load candidates");
    }

    return (await response.json()) as CandidatesResponse;
  };

  const handleRefresh = async () => {
    setIsLoading(true);
    setError("");

    try {
      const payload = await fetchCandidates();
      setData(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error while loading candidates");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;

    const hydrate = async () => {
      try {
        const payload = await fetchCandidates();
        if (isMounted) {
          setData(payload);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Unknown error while loading candidates");
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

  const filteredCandidates = useMemo(() => {
    const candidates = data?.candidates ?? [];
    const queryTokens = normalizeSearchText(query)
      .split(" ")
      .map((token) => token.trim())
      .filter(Boolean);

    return candidates.filter((candidate) => {
      const passesOpenToWork = !onlyOpenToWork || candidate.open_to_work;
      if (!passesOpenToWork) {
        return false;
      }

      const candidateMode = normalizeWorkMode(candidate.work_location_preference || candidate.remote_preference || "");
      if (workModeFilter !== "all" && candidateMode !== workModeFilter) {
        return false;
      }

      if (queryTokens.length === 0) {
        return true;
      }

      const haystack = normalizeSearchText(
        [
          candidate.name,
          candidate.role,
          candidate.city,
          candidate.remote_preference,
          candidate.work_location_preference || "",
          ...(candidate.skills ?? []),
        ].join(" ")
      );

      return queryTokens.every((token) => haystack.includes(token));
    });
  }, [data, onlyOpenToWork, query, workModeFilter]);

  const totalPages = Math.ceil(filteredCandidates.length / ITEMS_PER_PAGE);
  const paginatedCandidates = filteredCandidates.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  const openToWorkCount = useMemo(
    () => (data?.candidates ?? []).filter((candidate) => candidate.open_to_work).length,
    [data]
  );

  const remoteFriendlyCount = useMemo(
    () =>
      (data?.candidates ?? []).filter((candidate) => {
        const mode = normalizeWorkMode(candidate.work_location_preference || candidate.remote_preference || "");
        return mode === "remote" || mode === "hybrid" || mode === "flexible";
      }).length,
    [data]
  );

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [query, onlyOpenToWork, workModeFilter]);

  return (
    <main className="relative min-h-screen overflow-x-hidden">
      <AuroraBackground />
      <Navbar />

      <div className="relative z-10 mx-auto w-full max-w-[1400px] px-6 pt-[120px] pb-20">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="font-fustat text-4xl font-bold text-white">Candidates</h1>
            <p className="mt-2 text-white/65">Explore the full candidate pool and quickly filter by fit signals.</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-white/60">
              Source: {data?.source ?? "-"}
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

        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="glassmorphism rounded-2xl border border-white/10 p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-white/50">Total</p>
            <p className="mt-3 flex items-center gap-2 text-3xl font-bold text-white">
              <Users className="h-6 w-6 text-[#5AE14C]" />
              {data?.count ?? 0}
            </p>
          </div>
          <div className="glassmorphism rounded-2xl border border-white/10 p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-white/50">Open To Work</p>
            <p className="mt-3 flex items-center gap-2 text-3xl font-bold text-white">
              <Briefcase className="h-6 w-6 text-blue-300" />
              {openToWorkCount}
            </p>
          </div>
          <div className="glassmorphism rounded-2xl border border-white/10 p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-white/50">Remote Friendly</p>
            <p className="mt-3 flex items-center gap-2 text-3xl font-bold text-white">
              <Globe2 className="h-6 w-6 text-cyan-300" />
              {remoteFriendlyCount}
            </p>
          </div>
        </div>

        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <label className="relative w-full md:max-w-md">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/40" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by keywords (name role location skill)"
              className="w-full rounded-xl border border-white/15 bg-white/5 py-2.5 pl-10 pr-4 text-sm text-white placeholder:text-white/40 outline-none transition-colors focus:border-[#5AE14C]/60"
            />
          </label>

          <div className="flex flex-wrap items-center gap-3">
            <select
              value={workModeFilter}
              onChange={(event) => setWorkModeFilter(event.target.value)}
              className="rounded-xl border border-white/15 bg-white/5 px-3 py-2.5 text-sm text-white outline-none transition-colors focus:border-[#5AE14C]/60"
            >
              <option value="all" className="bg-[#0a1017]">All Work Modes</option>
              <option value="remote" className="bg-[#0a1017]">Remote Only</option>
              <option value="onsite" className="bg-[#0a1017]">On-site Only</option>
              <option value="hybrid" className="bg-[#0a1017]">Hybrid</option>
              <option value="flexible" className="bg-[#0a1017]">Flexible</option>
            </select>

            <label className="inline-flex items-center gap-2 text-sm font-medium text-white/80">
              <input
                type="checkbox"
                checked={onlyOpenToWork}
                onChange={(event) => setOnlyOpenToWork(event.target.checked)}
                className="h-4 w-4 rounded border-white/30 bg-white/5 text-[#5AE14C]"
              />
              Only open-to-work candidates
            </label>
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

        {!isLoading && !error && filteredCandidates.length === 0 && (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-white/70">
            No candidates matched the current filters.
          </div>
        )}

        {!isLoading && !error && paginatedCandidates.length > 0 && (
          <>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {paginatedCandidates.map((candidate) => (
                <article
                  key={candidate.id}
                  className="glassmorphism rounded-2xl border border-white/10 p-5 transition-colors hover:border-white/20"
                >
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div>
                      <h2 className="text-lg font-semibold text-white">{candidate.name}</h2>
                      <p className="text-sm text-white/65">{candidate.role}</p>
                    </div>
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                        candidate.open_to_work
                          ? "border border-[#5AE14C]/30 bg-[#5AE14C]/10 text-[#5AE14C]"
                          : "border border-white/20 bg-white/5 text-white/60"
                      }`}
                    >
                      {candidate.open_to_work ? "Open" : "Passive"}
                    </span>
                  </div>

                  <div className="mb-3 flex flex-wrap gap-2 text-xs text-white/70">
                    <span className="rounded-md border border-white/10 bg-white/5 px-2 py-1">{candidate.city}</span>
                    <span className="rounded-md border border-white/10 bg-white/5 px-2 py-1">
                      {candidate.work_location_preference || candidate.remote_preference}
                    </span>
                    <span className="rounded-md border border-white/10 bg-white/5 px-2 py-1">
                      {candidate.years_experience} YOE
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {candidate.skills.slice(0, 6).map((skill) => (
                      <span key={`${candidate.id}-${skill}`} className="rounded-full bg-white/8 px-2.5 py-1 text-xs text-white/80">
                        {skill}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-10 flex items-center justify-center gap-4">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-2 rounded-lg bg-white/5 border border-white/10 text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/10 transition-colors"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <div className="flex items-center gap-2">
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                    <button
                      key={page}
                      onClick={() => setCurrentPage(page)}
                      className={`w-10 h-10 rounded-lg flex items-center justify-center text-sm font-semibold transition-all ${
                        currentPage === page
                          ? "bg-[#5AE14C] text-black shadow-[0_0_15px_rgba(90,225,76,0.4)]"
                          : "bg-white/5 border border-white/10 text-white/70 hover:bg-white/10"
                      }`}
                    >
                      {page}
                    </button>
                  ))}
                </div>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="p-2 rounded-lg bg-white/5 border border-white/10 text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/10 transition-colors"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}
