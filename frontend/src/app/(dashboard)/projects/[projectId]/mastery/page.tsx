"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Award, TrendingUp, Minus, AlertTriangle, Sparkles, BookOpen, ArrowRight, CheckCircle2, Zap } from "lucide-react";
import { ApiClient } from "@/lib/api";
import { ConceptMastery, Recommendation } from "@/types";
import DocumentViewerModal from "@/components/DocumentViewerModal";

export default function MasteryGrowthPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  const [masteries, setMasteries] = useState<ConceptMastery[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewerState, setViewerState] = useState<{
    isOpen: boolean;
    materialId?: string;
    documentTitle?: string;
    initialPage?: number;
    highlightSnippet?: string;
  } | null>(null);

  useEffect(() => {
    fetchMasteryAndGrowth();
  }, [projectId]);

  const fetchMasteryAndGrowth = async () => {
    try {
      const mData = await ApiClient.request<ConceptMastery[]>(`/projects/${projectId}/mastery`);
      setMasteries(mData);
      const rData = await ApiClient.request<Recommendation[]>(`/projects/${projectId}/recommendations`);
      setRecommendations(rData);
    } catch (err) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const improving = masteries.filter((m) => m.trend_state === "IMPROVING");
  const stable = masteries.filter((m) => m.trend_state === "STABLE");
  const attention = masteries.filter((m) => m.trend_state === "REQUIRING_ATTENTION");

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-800 bg-surface/50 backdrop-blur px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href={`/projects/${projectId}`}
            className="text-gray-400 hover:text-white p-2 rounded-lg hover:bg-surface transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Mastery &amp; Analytics</span>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Award className="w-5 h-5 text-emerald-400" /> Concept Mastery &amp; Growth
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href={`/projects/${projectId}/cheat-sheet`}
            className="bg-amber-950/60 hover:bg-amber-900 border border-amber-800 text-amber-300 text-xs font-medium px-3.5 py-2 rounded-lg transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <Zap className="w-3.5 h-3.5 text-amber-400" /> Exam Cheat Sheet
          </Link>
          <Link
            href={`/projects/${projectId}/quiz`}
            className="bg-primary-600 hover:bg-primary-500 text-white text-xs font-medium px-4 py-2 rounded-lg transition-colors flex items-center gap-1.5 shadow-lg shadow-blue-500/20"
          >
            <Sparkles className="w-3.5 h-3.5" /> Practice Weak Concepts
          </Link>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8 space-y-10">
        {/* Actionable Recommendation Hero: Answers "What should I do next?" */}
        {recommendations.length > 0 && (
          <div className="p-6 rounded-2xl bg-gradient-to-r from-blue-950/40 via-surface to-surface border border-blue-900/60 shadow-xl">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-900/60 text-blue-300 text-xs font-semibold uppercase tracking-wider mb-3">
              <Sparkles className="w-3.5 h-3.5" /> Actionable Next Step
            </div>
            <h2 className="text-xl font-bold text-white mb-2">{recommendations[0].title}</h2>
            <p className="text-sm text-gray-300 max-w-2xl mb-6 leading-relaxed">
              {recommendations[0].reasoning}
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href={`/projects/${projectId}/quiz`}
                className="bg-primary-600 hover:bg-primary-500 text-white text-xs font-medium px-5 py-2.5 rounded-lg transition-colors flex items-center gap-2 shadow-lg shadow-blue-500/20"
              >
                Start Targeted Quiz <ArrowRight className="w-4 h-4" />
              </Link>
              {recommendations[0].target_payload?.page_number && (
                <button
                  onClick={() =>
                    setViewerState({
                      isOpen: true,
                      materialId: recommendations[0].target_payload?.material_id,
                      documentTitle: recommendations[0].target_payload?.document_title,
                      initialPage: recommendations[0].target_payload?.page_number,
                      highlightSnippet: recommendations[0].target_payload?.snippet,
                    })
                  }
                  className="bg-amber-950/80 hover:bg-amber-900 border border-amber-800 text-amber-300 text-xs font-semibold px-4 py-2.5 rounded-lg transition-all hover:scale-105 flex items-center gap-2 shadow-md"
                >
                  <BookOpen className="w-4 h-4" /> Open Supporting PDF (Page {recommendations[0].target_payload.page_number}) &rarr;
                </button>
              )}
              <Link
                href={`/projects/${projectId}/materials`}
                className="bg-surface hover:bg-surface-raised border border-gray-700 text-gray-300 hover:text-white text-xs font-medium px-4 py-2.5 rounded-lg transition-colors"
              >
                Review Source Materials
              </Link>
            </div>
          </div>
        )}

        {/* Concept Mastery Estimates Section */}
        <div>
          <h2 className="text-lg font-bold text-white mb-4">Estimated Concept Mastery Levels</h2>
          <div className="bg-surface border border-gray-800 rounded-xl p-6 divide-y divide-gray-800">
            {masteries.length === 0 ? (
              <p className="text-xs text-gray-500 text-center py-4">
                No assessments completed yet. Take an adaptive quiz to measure concept mastery.
              </p>
            ) : (
              masteries.map((m) => (
                <div key={m.id} className="py-4 first:pt-0 last:pb-0">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-white">{m.concept_name}</span>
                    <span className="text-sm font-extrabold text-blue-400">{m.mastery_score}%</span>
                  </div>
                  <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-2 rounded-full transition-all duration-700 ${
                        m.mastery_score >= 75
                          ? "bg-emerald-500"
                          : m.mastery_score >= 50
                          ? "bg-amber-500"
                          : "bg-rose-500"
                      }`}
                      style={{ width: `${m.mastery_score}%` }}
                    ></div>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-gray-500 mt-2">
                    <span>{m.total_attempts} attempts recorded</span>
                    <span className="capitalize">{m.trend_state.replace("_", " ").toLowerCase()}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Growth Analysis: Improving, Stable, Requiring Attention */}
        <div>
          <h2 className="text-lg font-bold text-white mb-4">Growth Analysis Trajectory</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Improving Column */}
            <div className="p-6 rounded-xl bg-surface border border-emerald-900/40 shadow-sm">
              <div className="flex items-center gap-2 text-emerald-400 text-sm font-bold uppercase tracking-wider mb-4">
                <TrendingUp className="w-4 h-4" /> Improving ({improving.length})
              </div>
              <div className="space-y-3">
                {improving.length === 0 ? (
                  <p className="text-xs text-gray-500">No concepts currently trending upward.</p>
                ) : (
                  improving.map((c) => (
                    <div key={c.id} className="p-3 rounded-lg bg-surface-raised border border-emerald-900/30">
                      <p className="text-xs font-semibold text-white">{c.concept_name}</p>
                      <p className="text-[11px] text-emerald-400 mt-0.5">Mastery: {c.mastery_score}%</p>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Stable Column */}
            <div className="p-6 rounded-xl bg-surface border border-amber-900/40 shadow-sm">
              <div className="flex items-center gap-2 text-amber-400 text-sm font-bold uppercase tracking-wider mb-4">
                <Minus className="w-4 h-4" /> Stable ({stable.length})
              </div>
              <div className="space-y-3">
                {stable.length === 0 ? (
                  <p className="text-xs text-gray-500">No concepts in stable baseline.</p>
                ) : (
                  stable.map((c) => (
                    <div key={c.id} className="p-3 rounded-lg bg-surface-raised border border-amber-900/30">
                      <p className="text-xs font-semibold text-white">{c.concept_name}</p>
                      <p className="text-[11px] text-amber-400 mt-0.5">Mastery: {c.mastery_score}%</p>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Requiring Attention Column */}
            <div className="p-6 rounded-xl bg-surface border border-rose-900/40 shadow-sm">
              <div className="flex items-center gap-2 text-rose-400 text-sm font-bold uppercase tracking-wider mb-4">
                <AlertTriangle className="w-4 h-4" /> Requiring Attention ({attention.length})
              </div>
              <div className="space-y-3">
                {attention.length === 0 ? (
                  <p className="text-xs text-gray-500">No high-risk concept deficits detected.</p>
                ) : (
                  attention.map((c) => (
                    <div key={c.id} className="p-3 rounded-lg bg-surface-raised border border-rose-900/30">
                      <p className="text-xs font-semibold text-white">{c.concept_name}</p>
                      <p className="text-[11px] text-rose-400 mt-0.5">
                        Mastery: {c.mastery_score}% ({c.consecutive_mistakes} consecutive errors)
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>

        {/* In-Browser Document Citation Reader Modal */}
        {viewerState?.isOpen && (
          <DocumentViewerModal
            projectId={projectId}
            materialId={viewerState.materialId}
            documentTitle={viewerState.documentTitle}
            initialPage={viewerState.initialPage}
            highlightSnippet={viewerState.highlightSnippet}
            onClose={() => setViewerState(null)}
          />
        )}
      </main>
    </div>
  );
}
