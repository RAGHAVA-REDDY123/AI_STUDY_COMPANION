"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, BookOpen, Brain, Sparkles, Award, BarChart3, ArrowRight, Target, AlertCircle, CheckCircle2, Zap } from "lucide-react";
import { ApiClient } from "@/lib/api";
import { ProjectSummary } from "@/types";
import DocumentViewerModal from "@/components/DocumentViewerModal";

export default function ProjectWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  const [summary, setSummary] = useState<ProjectSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [viewerState, setViewerState] = useState<{
    isOpen: boolean;
    materialId?: string;
    documentTitle?: string;
    initialPage?: number;
    highlightSnippet?: string;
  } | null>(null);

  useEffect(() => {
    fetchProjectSummary();
  }, [projectId]);

  const fetchProjectSummary = async () => {
    try {
      const data = await ApiClient.request<ProjectSummary>(`/projects/${projectId}/summary`);
      setSummary(data);
    } catch (err) {
      router.push("/dashboard");
    } finally {
      setLoading(false);
    }
  };

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
            href="/dashboard"
            className="text-gray-400 hover:text-white p-2 rounded-lg hover:bg-surface transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <span className="text-xs font-semibold text-primary-400 uppercase tracking-wider">Project Workspace</span>
            <h1 className="text-xl font-bold text-white">{summary?.name || "Workspace"}</h1>
          </div>
        </div>

        {/* Global Nav for Project Sub-areas */}
        <nav className="flex items-center gap-2">
          <Link
            href={`/projects/${projectId}/materials`}
            className="px-3 py-1.5 rounded-lg text-xs font-medium text-gray-300 hover:text-white hover:bg-surface transition-colors flex items-center gap-1.5"
          >
            <BookOpen className="w-3.5 h-3.5 text-blue-400" /> Materials
          </Link>
          <Link
            href={`/projects/${projectId}/tutor`}
            className="px-3 py-1.5 rounded-lg text-xs font-medium text-gray-300 hover:text-white hover:bg-surface transition-colors flex items-center gap-1.5"
          >
            <Brain className="w-3.5 h-3.5 text-indigo-400" /> AI Tutor
          </Link>
          <Link
            href={`/projects/${projectId}/quiz`}
            className="px-3 py-1.5 rounded-lg text-xs font-medium text-gray-300 hover:text-white hover:bg-surface transition-colors flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Adaptive Quiz
          </Link>
          <Link
            href={`/projects/${projectId}/mastery`}
            className="px-3 py-1.5 rounded-lg text-xs font-medium text-gray-300 hover:text-white hover:bg-surface transition-colors flex items-center gap-1.5"
          >
            <Award className="w-3.5 h-3.5 text-emerald-400" /> Mastery &amp; Growth
          </Link>
          <Link
            href={`/projects/${projectId}/analytics`}
            className="px-3 py-1.5 rounded-lg text-xs font-medium text-gray-300 hover:text-white hover:bg-surface transition-colors flex items-center gap-1.5"
          >
            <BarChart3 className="w-3.5 h-3.5 text-cyan-400" /> Analytics
          </Link>
          <Link
            href={`/projects/${projectId}/cheat-sheet`}
            className="px-3 py-1.5 rounded-lg text-xs font-medium text-amber-300 hover:text-white bg-amber-950/40 hover:bg-amber-900/60 border border-amber-800/60 transition-colors flex items-center gap-1.5"
          >
            <Zap className="w-3.5 h-3.5 text-amber-400" /> Exam Cheat Sheet
          </Link>
        </nav>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        {/* Project Target Goal Banner */}
        <div className="p-4 rounded-xl bg-surface border border-gray-800 mb-8 flex items-start gap-3">
          <Target className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider block mb-0.5">
              Active Learning Goal
            </span>
            <p className="text-sm text-gray-200">{summary?.learning_goal}</p>
          </div>
        </div>

        {/* Metric Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-8">
          <div className="p-6 rounded-xl bg-surface border border-gray-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Materials</span>
              <BookOpen className="w-5 h-5 text-blue-400" />
            </div>
            <div className="text-3xl font-extrabold text-white">{summary?.total_materials}</div>
            <p className="text-xs text-gray-500 mt-1">Uploaded &amp; indexed source PDFs</p>
          </div>

          <div className="p-6 rounded-xl bg-surface border border-gray-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Concepts Extracted</span>
              <Brain className="w-5 h-5 text-indigo-400" />
            </div>
            <div className="text-3xl font-extrabold text-white">{summary?.total_concepts}</div>
            <p className="text-xs text-gray-500 mt-1">Atomic domain concepts tracked</p>
          </div>

          <div className="p-6 rounded-xl bg-surface border border-gray-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Average Mastery</span>
              <Award className="w-5 h-5 text-emerald-400" />
            </div>
            <div className="text-3xl font-extrabold text-white">{summary?.average_mastery}%</div>
            <div className="w-full bg-gray-800 rounded-full h-1.5 mt-3">
              <div
                className="bg-emerald-500 h-1.5 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, summary?.average_mastery || 0)}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Active Recommendation Hero */}
        {summary?.active_recommendation && (
          <div className="mb-10 p-6 rounded-2xl bg-gradient-to-r from-blue-950/30 via-surface to-surface border border-blue-900/60 shadow-xl">
            <div className="flex items-center justify-between mb-3">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-blue-900/60 text-blue-300 text-xs font-semibold">
                <Sparkles className="w-3.5 h-3.5" /> Next Action Recommended
              </div>
              {summary.active_recommendation.target_payload?.page_number && (
                <button
                  onClick={() =>
                    setViewerState({
                      isOpen: true,
                      materialId: summary.active_recommendation?.target_payload?.material_id,
                      documentTitle: summary.active_recommendation?.target_payload?.document_title,
                      initialPage: summary.active_recommendation?.target_payload?.page_number,
                      highlightSnippet: summary.active_recommendation?.target_payload?.snippet,
                    })
                  }
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-amber-950/80 hover:bg-amber-900 border border-amber-800 text-amber-300 text-xs font-semibold transition-all hover:scale-105 shadow-sm"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  <span>Open Cited PDF (Page {summary.active_recommendation.target_payload.page_number}) &rarr;</span>
                </button>
              )}
            </div>
            <h3 className="text-lg font-bold text-white mb-1">
              {summary.active_recommendation.title}
            </h3>
            <p className="text-xs text-gray-300 mb-4 max-w-2xl leading-relaxed">
              {summary.active_recommendation.reasoning}
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href={`/projects/${projectId}/quiz`}
                className="bg-primary-600 hover:bg-primary-500 text-white text-xs font-medium px-4 py-2 rounded-lg transition-colors flex items-center gap-2 shadow-lg shadow-blue-500/20"
              >
                Launch Targeted Assessment <ArrowRight className="w-3.5 h-3.5" />
              </Link>
              {summary.active_recommendation.target_payload?.page_number && (
                <button
                  onClick={() =>
                    setViewerState({
                      isOpen: true,
                      materialId: summary.active_recommendation?.target_payload?.material_id,
                      initialPage: summary.active_recommendation?.target_payload?.page_number,
                      highlightSnippet: summary.active_recommendation?.target_payload?.snippet,
                    })
                  }
                  className="bg-surface hover:bg-surface-raised border border-gray-700 text-gray-200 text-xs font-medium px-4 py-2 rounded-lg transition-colors flex items-center gap-1.5"
                >
                  <BookOpen className="w-3.5 h-3.5 text-amber-400" /> Read Page {summary.active_recommendation.target_payload.page_number} in Viewer
                </button>
              )}
            </div>
          </div>
        )}

        {/* The Closed Learning Loop Quick Actions */}
        <h3 className="text-base font-bold text-white mb-4">Core Learning Loop Navigation</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          <Link
            href={`/projects/${projectId}/materials`}
            className="p-5 rounded-xl bg-surface border border-gray-800 hover:border-blue-700 transition-all group flex flex-col justify-between"
          >
            <div>
              <BookOpen className="w-6 h-6 text-blue-400 mb-3" />
              <h4 className="font-semibold text-white text-sm mb-1 group-hover:text-blue-400 transition-colors">
                1. Materials &amp; Ingestion
              </h4>
              <p className="text-xs text-gray-400 leading-relaxed">
                Upload PDFs, inspect extraction status, and view atomic concepts.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-gray-800 flex items-center justify-between text-xs text-gray-500 group-hover:text-white">
              <span>Manage Materials</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </Link>

          <Link
            href={`/projects/${projectId}/tutor`}
            className="p-5 rounded-xl bg-surface border border-gray-800 hover:border-indigo-700 transition-all group flex flex-col justify-between"
          >
            <div>
              <Brain className="w-6 h-6 text-indigo-400 mb-3" />
              <h4 className="font-semibold text-white text-sm mb-1 group-hover:text-indigo-400 transition-colors">
                2. AI Tutor &amp; Citations
              </h4>
              <p className="text-xs text-gray-400 leading-relaxed">
                Chat with an AI tutor strictly grounded with page-level citations.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-gray-800 flex items-center justify-between text-xs text-gray-500 group-hover:text-white">
              <span>Start Session</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </Link>

          <Link
            href={`/projects/${projectId}/quiz`}
            className="p-5 rounded-xl bg-surface border border-gray-800 hover:border-amber-700 transition-all group flex flex-col justify-between"
          >
            <div>
              <Sparkles className="w-6 h-6 text-amber-400 mb-3" />
              <h4 className="font-semibold text-white text-sm mb-1 group-hover:text-amber-400 transition-colors">
                3. Adaptive Quiz &amp; Rubrics
              </h4>
              <p className="text-xs text-gray-400 leading-relaxed">
                Test understanding via MCQs and open-ended rubric evaluations.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-gray-800 flex items-center justify-between text-xs text-gray-500 group-hover:text-white">
              <span>Take Quiz</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </Link>

          <Link
            href={`/projects/${projectId}/mastery`}
            className="p-5 rounded-xl bg-surface border border-gray-800 hover:border-emerald-700 transition-all group flex flex-col justify-between"
          >
            <div>
              <Award className="w-6 h-6 text-emerald-400 mb-3" />
              <h4 className="font-semibold text-white text-sm mb-1 group-hover:text-emerald-400 transition-colors">
                4. Mastery &amp; Growth
              </h4>
              <p className="text-xs text-gray-400 leading-relaxed">
                Inspect concept trajectory (Improving, Stable, Requiring Attention).
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-gray-800 flex items-center justify-between text-xs text-gray-500 group-hover:text-white">
              <span>View Trajectory</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </Link>

          <Link
            href={`/projects/${projectId}/analytics`}
            className="p-5 rounded-xl bg-surface border border-gray-800 hover:border-cyan-700 transition-all group flex flex-col justify-between"
          >
            <div>
              <BarChart3 className="w-6 h-6 text-cyan-400 mb-3" />
              <h4 className="font-semibold text-white text-sm mb-1 group-hover:text-cyan-400 transition-colors">
                5. Analytics &amp; Visual Trends
              </h4>
              <p className="text-xs text-gray-400 leading-relaxed">
                Recharts graphs for quiz scores, mastery velocity, and audit event feeds.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-gray-800 flex items-center justify-between text-xs text-gray-500 group-hover:text-white">
              <span>View Analytics</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </Link>

          <Link
            href={`/projects/${projectId}/cheat-sheet`}
            className="p-5 rounded-xl bg-gradient-to-b from-amber-950/20 via-surface to-surface border border-amber-900/50 hover:border-amber-500 transition-all group flex flex-col justify-between shadow-lg hover:shadow-amber-500/10"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <Zap className="w-6 h-6 text-amber-400" />
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  High Yield
                </span>
              </div>
              <h4 className="font-semibold text-white text-sm mb-1 group-hover:text-amber-400 transition-colors">
                6. Exam Revision &amp; Cheat Sheet
              </h4>
              <p className="text-xs text-gray-400 leading-relaxed">
                Personalized study sheet with student mistake traps, cited formulas, rapid-fire Q&amp;A, and print export.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-gray-800 flex items-center justify-between text-xs text-amber-400 group-hover:text-amber-300 font-medium">
              <span>Open Study Sheet</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </div>
          </Link>
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
