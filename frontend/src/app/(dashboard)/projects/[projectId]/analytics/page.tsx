"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  BarChart3,
  Award,
  Sparkles,
  Flame,
  CheckCircle2,
  AlertTriangle,
  Brain,
  BookOpen,
  TrendingUp,
  Activity,
  HelpCircle,
  Layers,
  ArrowUpRight,
  Clock,
  FileText
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Legend
} from "recharts";

import { ApiClient } from "@/lib/api";
import { ProjectAnalyticsOut } from "@/types";

const MISTAKE_COLORS = ["#ef4444", "#f59e0b", "#8b5cf6", "#ec4899", "#3b82f6"];

export default function ProjectAnalyticsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  const [analytics, setAnalytics] = useState<ProjectAnalyticsOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAnalytics();
  }, [projectId]);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const data = await ApiClient.request<ProjectAnalyticsOut>(`/projects/${projectId}/analytics`);
      setAnalytics(data);
    } catch (err: any) {
      setError(err.message || "Failed to load project analytics");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-cyan-500"></div>
          <p className="text-sm text-gray-400">Computing project analytics &amp; mastery trends...</p>
        </div>
      </div>
    );
  }

  if (error || !analytics) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <div className="max-w-md w-full p-6 rounded-2xl bg-surface border border-gray-800 text-center">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-white mb-2">Analytics Unavailable</h2>
          <p className="text-sm text-gray-400 mb-6">{error || "No data recorded for this project yet."}</p>
          <Link
            href={`/projects/${projectId}`}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Workspace
          </Link>
        </div>
      </div>
    );
  }

  const { overview, concept_metrics, quiz_history, mistake_distribution, daily_activity, recent_events } = analytics;

  return (
    <div className="min-h-screen bg-background flex flex-col text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 bg-surface/60 backdrop-blur px-6 py-4 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-4">
          <Link
            href={`/projects/${projectId}`}
            className="text-gray-400 hover:text-white p-2 rounded-lg hover:bg-surface transition-colors"
            title="Back to Project"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider">PRD Observability</span>
              <span className="text-xs bg-cyan-950/80 border border-cyan-800 text-cyan-300 px-2 py-0.5 rounded-full font-medium">
                Live Telemetry
              </span>
            </div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-cyan-400" /> Learning Analytics &amp; Growth Trends
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href={`/projects/${projectId}/quiz`}
            className="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-primary-600 hover:bg-primary-500 text-white transition-colors flex items-center gap-1.5 shadow-lg shadow-blue-500/10"
          >
            <Sparkles className="w-3.5 h-3.5" /> Take Adaptive Quiz
          </Link>
          <Link
            href={`/projects/${projectId}/tutor`}
            className="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-surface hover:bg-surface-raised border border-gray-700 text-gray-200 transition-colors flex items-center gap-1.5"
          >
            <Brain className="w-3.5 h-3.5 text-indigo-400" /> Ask AI Tutor
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 space-y-8">
        {/* Section 1: Executive KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {/* Card 1: Overall Mastery */}
          <div className="p-4 rounded-xl bg-surface border border-gray-800 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-gray-400 mb-2">
              <span className="text-xs uppercase font-semibold tracking-wider">Overall Mastery</span>
              <Award className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <div className="text-2xl font-black text-white">{overview.overall_mastery}%</div>
              <p className="text-[11px] text-emerald-400 font-medium truncate mt-0.5">{overview.mastery_status}</p>
            </div>
          </div>

          {/* Card 2: Quiz Average */}
          <div className="p-4 rounded-xl bg-surface border border-gray-800 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-gray-400 mb-2">
              <span className="text-xs uppercase font-semibold tracking-wider">Avg Quiz Score</span>
              <TrendingUp className="w-4 h-4 text-blue-400" />
            </div>
            <div>
              <div className="text-2xl font-black text-white">{overview.average_quiz_score}%</div>
              <p className="text-[11px] text-gray-400 mt-0.5">{overview.total_quizzes_completed} completed</p>
            </div>
          </div>

          {/* Card 3: Accuracy Rate */}
          <div className="p-4 rounded-xl bg-surface border border-gray-800 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-gray-400 mb-2">
              <span className="text-xs uppercase font-semibold tracking-wider">Accuracy</span>
              <CheckCircle2 className="w-4 h-4 text-cyan-400" />
            </div>
            <div>
              <div className="text-2xl font-black text-white">{overview.accuracy_rate}%</div>
              <p className="text-[11px] text-gray-400 mt-0.5">{overview.total_questions_answered} questions</p>
            </div>
          </div>

          {/* Card 4: Study Streak */}
          <div className="p-4 rounded-xl bg-surface border border-gray-800 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-gray-400 mb-2">
              <span className="text-xs uppercase font-semibold tracking-wider">Active Streak</span>
              <Flame className="w-4 h-4 text-amber-400" />
            </div>
            <div>
              <div className="text-2xl font-black text-white flex items-center gap-1.5">
                {overview.streak_days} <span className="text-sm font-normal text-amber-300">days</span>
              </div>
              <p className="text-[11px] text-amber-400/80 mt-0.5">Consecutive learning</p>
            </div>
          </div>

          {/* Card 5: Knowledge Chunks */}
          <div className="p-4 rounded-xl bg-surface border border-gray-800 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-gray-400 mb-2">
              <span className="text-xs uppercase font-semibold tracking-wider">Indexed Chunks</span>
              <Layers className="w-4 h-4 text-purple-400" />
            </div>
            <div>
              <div className="text-2xl font-black text-white">{overview.total_chunks}</div>
              <p className="text-[11px] text-gray-400 mt-0.5">{overview.total_materials} documents</p>
            </div>
          </div>

          {/* Card 6: AI Interactions */}
          <div className="p-4 rounded-xl bg-surface border border-gray-800 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-gray-400 mb-2">
              <span className="text-xs uppercase font-semibold tracking-wider">AI Queries</span>
              <Brain className="w-4 h-4 text-pink-400" />
            </div>
            <div>
              <div className="text-2xl font-black text-white">{overview.ai_queries_count}</div>
              <p className="text-[11px] text-gray-400 mt-0.5">Grounded RAG ops</p>
            </div>
          </div>
        </div>

        {/* Section 2: Core Visual Analytics Graphs */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Graph 1: Quiz Score Trajectory */}
          <div className="p-6 rounded-2xl bg-surface border border-gray-800 shadow-md flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-cyan-400" /> Quiz Performance Trajectory
                </h3>
                <p className="text-xs text-gray-400">Score history with 70% passing threshold benchmark</p>
              </div>
              <span className="text-xs font-semibold px-2.5 py-1 rounded bg-surface-raised text-gray-300 border border-gray-700">
                Target: 70%
              </span>
            </div>

            <div className="h-64 w-full">
              {quiz_history.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-6 border border-dashed border-gray-800 rounded-xl">
                  <HelpCircle className="w-8 h-8 text-gray-600 mb-2" />
                  <p className="text-xs text-gray-400 mb-3">No completed quizzes yet</p>
                  <Link
                    href={`/projects/${projectId}/quiz`}
                    className="text-xs font-medium text-cyan-400 hover:text-cyan-300 underline"
                  >
                    Take your first adaptive quiz &rarr;
                  </Link>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={quiz_history} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="scoreGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                    <XAxis dataKey="completed_at" stroke="#6b7280" fontSize={11} tickLine={false} />
                    <YAxis stroke="#6b7280" fontSize={11} domain={[0, 100]} tickLine={false} unit="%" />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#111827", borderColor: "#374151", borderRadius: "0.75rem", fontSize: "12px", color: "#f3f4f6" }}
                      formatter={(val: any) => [`${val}%`, "Score"]}
                    />
                    <ReferenceLine y={70} stroke="#10b981" strokeDasharray="4 4" label={{ value: "Mastery (70%)", fill: "#10b981", fontSize: 10, position: "insideTopRight" }} />
                    <Area type="monotone" dataKey="score_percentage" stroke="#06b6d4" strokeWidth={2.5} fillOpacity={1} fill="url(#scoreGradient)" name="Score" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Graph 2: Concept Mastery Ranking & Distribution */}
          <div className="p-6 rounded-2xl bg-surface border border-gray-800 shadow-md flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Award className="w-4 h-4 text-emerald-400" /> Concept Mastery Distribution
                </h3>
                <p className="text-xs text-gray-400">Current score estimation per core curriculum concept</p>
              </div>
              <div className="flex items-center gap-2 text-[10px]">
                <span className="flex items-center gap-1 text-emerald-400"><span className="w-2 h-2 rounded-full bg-emerald-500"></span> &ge;70%</span>
                <span className="flex items-center gap-1 text-amber-400"><span className="w-2 h-2 rounded-full bg-amber-500"></span> 40-69%</span>
                <span className="flex items-center gap-1 text-red-400"><span className="w-2 h-2 rounded-full bg-red-500"></span> &lt;40%</span>
              </div>
            </div>

            <div className="h-64 w-full">
              {concept_metrics.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-6 border border-dashed border-gray-800 rounded-xl">
                  <HelpCircle className="w-8 h-8 text-gray-600 mb-2" />
                  <p className="text-xs text-gray-400 mb-3">No concepts extracted yet</p>
                  <Link
                    href={`/projects/${projectId}/materials`}
                    className="text-xs font-medium text-cyan-400 hover:text-cyan-300 underline"
                  >
                    Upload study materials &rarr;
                  </Link>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={concept_metrics.slice(0, 8)} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
                    <XAxis type="number" domain={[0, 100]} stroke="#6b7280" fontSize={11} unit="%" />
                    <YAxis dataKey="concept_name" type="category" width={110} stroke="#9ca3af" fontSize={11} tickLine={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#111827", borderColor: "#374151", borderRadius: "0.75rem", fontSize: "12px", color: "#f3f4f6" }}
                      formatter={(val: any) => [`${val}%`, "Mastery"]}
                    />
                    <Bar dataKey="mastery_score" radius={[0, 6, 6, 0]}>
                      {concept_metrics.map((entry, index) => {
                        const color = entry.mastery_score >= 70 ? "#10b981" : entry.mastery_score >= 40 ? "#f59e0b" : "#ef4444";
                        return <Cell key={`cell-${index}`} fill={color} />;
                      })}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>

        {/* Section 3: Study Activity Velocity & Cognitive Mistake Types */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 14-Day Velocity BarChart (2 cols) */}
          <div className="lg:col-span-2 p-6 rounded-2xl bg-surface border border-gray-800 shadow-md">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-indigo-400" /> 14-Day Learning Velocity
                </h3>
                <p className="text-xs text-gray-400">Daily volume of learning events (Quizzes, Tutor conversations, Uploads)</p>
              </div>
              <span className="text-xs font-semibold px-2.5 py-1 rounded bg-indigo-950/80 border border-indigo-800 text-indigo-300">
                Streak: {overview.streak_days} Days
              </span>
            </div>

            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={daily_activity} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                  <XAxis dataKey="date" stroke="#6b7280" fontSize={10} tickLine={false} />
                  <YAxis stroke="#6b7280" fontSize={10} allowDecimals={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#111827", borderColor: "#374151", borderRadius: "0.75rem", fontSize: "12px", color: "#f3f4f6" }}
                    formatter={(val: any) => [val, "Learning Actions"]}
                  />
                  <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} name="Actions" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Cognitive Error Type Donut / Breakdown (1 col) */}
          <div className="p-6 rounded-2xl bg-surface border border-gray-800 shadow-md flex flex-col justify-between">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2 mb-1">
                <AlertTriangle className="w-4 h-4 text-amber-400" /> Error Type Distribution
              </h3>
              <p className="text-xs text-gray-400 mb-4">Rubric-classified cognitive mistakes</p>

              {mistake_distribution.length === 0 ? (
                <div className="h-44 flex flex-col items-center justify-center text-center p-4 border border-dashed border-gray-800 rounded-xl">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400 mb-2" />
                  <p className="text-xs text-gray-300 font-medium">Zero errors recorded</p>
                  <p className="text-[11px] text-gray-500 mt-1">Excellent performance or no mistakes flagged</p>
                </div>
              ) : (
                <div className="space-y-3 mt-2">
                  {mistake_distribution.map((m, idx) => (
                    <div key={m.mistake_type} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full"
                          style={{ backgroundColor: MISTAKE_COLORS[idx % MISTAKE_COLORS.length] }}
                        ></span>
                        <span className="text-gray-300">{m.mistake_type}</span>
                      </div>
                      <span className="font-bold text-white bg-surface-raised px-2 py-0.5 rounded border border-gray-800">
                        {m.count}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="pt-4 border-t border-gray-800 mt-4 text-[11px] text-gray-400">
              Assists the AI in scheduling targeted remediation workflows.
            </div>
          </div>
        </div>

        {/* Section 4: Deep-Dive Concept Mastery Table */}
        <div className="p-6 rounded-2xl bg-surface border border-gray-800 shadow-md">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-white">Curriculum Concept Drill-Down</h3>
              <p className="text-xs text-gray-400">Detailed performance metrics and growth status per concept</p>
            </div>
            <span className="text-xs text-gray-400 font-medium">{concept_metrics.length} Total Concepts</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-[11px] uppercase tracking-wider text-gray-400 border-b border-gray-800 bg-surface-raised/40">
                <tr>
                  <th className="py-3 px-4">Concept Name</th>
                  <th className="py-3 px-4">Mastery Score</th>
                  <th className="py-3 px-4">Trend Status</th>
                  <th className="py-3 px-4 text-center">Attempts</th>
                  <th className="py-3 px-4 text-center">Consecutive Errors</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {concept_metrics.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-gray-500">
                      No concepts available for this project.
                    </td>
                  </tr>
                ) : (
                  concept_metrics.map((c) => (
                    <tr key={c.concept_id} className="hover:bg-surface-raised/50 transition-colors">
                      <td className="py-3 px-4 font-medium text-white">{c.concept_name}</td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-24 h-2 bg-gray-800 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                c.mastery_score >= 70
                                  ? "bg-emerald-500"
                                  : c.mastery_score >= 40
                                  ? "bg-amber-500"
                                  : "bg-red-500"
                              }`}
                              style={{ width: `${c.mastery_score}%` }}
                            ></div>
                          </div>
                          <span className="font-bold text-gray-200">{c.mastery_score}%</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border ${
                            c.trend_state === "IMPROVING"
                              ? "bg-emerald-950/80 text-emerald-400 border-emerald-800"
                              : c.trend_state === "REQUIRING_ATTENTION"
                              ? "bg-red-950/80 text-red-400 border-red-800"
                              : "bg-gray-800 text-gray-300 border-gray-700"
                          }`}
                        >
                          {c.trend_state.replace("_", " ")}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center text-gray-300">{c.total_attempts}</td>
                      <td className="py-3 px-4 text-center">
                        <span className={c.consecutive_mistakes >= 2 ? "text-red-400 font-bold" : "text-gray-400"}>
                          {c.consecutive_mistakes}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Link
                          href={`/projects/${projectId}/quiz`}
                          className="inline-flex items-center gap-1 text-cyan-400 hover:text-cyan-300 font-medium"
                        >
                          Practice <ArrowUpRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Section 5: Recent Activity Audit Stream */}
        <div className="p-6 rounded-2xl bg-surface border border-gray-800 shadow-md">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Clock className="w-4 h-4 text-gray-400" /> Learning Event Audit Trail
              </h3>
              <p className="text-xs text-gray-400">Chronological activity events recorded by the platform</p>
            </div>
            <span className="text-xs text-gray-500 font-medium">Past {recent_events.length} Events</span>
          </div>

          <div className="space-y-3">
            {recent_events.length === 0 ? (
              <p className="text-xs text-gray-500 py-4 text-center">No activity recorded yet.</p>
            ) : (
              recent_events.map((evt) => {
                let badgeColor = "bg-gray-800 text-gray-300 border-gray-700";
                let icon = <FileText className="w-3.5 h-3.5" />;

                if (evt.event_type.includes("QUIZ")) {
                  badgeColor = "bg-amber-950/80 text-amber-400 border-amber-800";
                  icon = <Sparkles className="w-3.5 h-3.5" />;
                } else if (evt.event_type.includes("TUTOR")) {
                  badgeColor = "bg-indigo-950/80 text-indigo-400 border-indigo-800";
                  icon = <Brain className="w-3.5 h-3.5" />;
                } else if (evt.event_type.includes("MATERIAL")) {
                  badgeColor = "bg-blue-950/80 text-blue-400 border-blue-800";
                  icon = <BookOpen className="w-3.5 h-3.5" />;
                } else if (evt.event_type.includes("MASTERY")) {
                  badgeColor = "bg-emerald-950/80 text-emerald-400 border-emerald-800";
                  icon = <Award className="w-3.5 h-3.5" />;
                }

                return (
                  <div
                    key={evt.id}
                    className="p-3 rounded-xl bg-surface-raised/60 border border-gray-800/80 flex items-center justify-between gap-4 text-xs hover:border-gray-700 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <span className={`p-1.5 rounded-lg border ${badgeColor}`}>{icon}</span>
                      <div>
                        <div className="font-semibold text-white">
                          {evt.event_type.replace(/_/g, " ")}
                        </div>
                        <p className="text-[11px] text-gray-400 truncate max-w-md">
                          {evt.payload.filename
                            ? `File: ${evt.payload.filename}`
                            : evt.payload.concept_name
                            ? `Concept: ${evt.payload.concept_name} (New score: ${evt.payload.after}%)`
                            : evt.payload.query_preview
                            ? `Question: "${evt.payload.query_preview}"`
                            : evt.payload.score !== undefined
                            ? `Quiz completed with ${evt.payload.score}%`
                            : JSON.stringify(evt.payload)}
                        </p>
                      </div>
                    </div>

                    <span className="text-[10px] text-gray-500 whitespace-nowrap">
                      {new Date(evt.created_at).toLocaleString([], {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit"
                      })}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
