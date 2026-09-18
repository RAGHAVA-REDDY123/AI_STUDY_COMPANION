"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Shield,
  Users,
  Layers,
  BookOpen,
  Cpu,
  DollarSign,
  Activity,
  AlertCircle,
  RefreshCw,
  Search,
  CheckCircle2,
  XCircle,
  Clock,
  Play,
  GitCompare,
  Filter,
  Eye,
  FileText,
  AlertTriangle,
  Zap,
  BarChart3
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid
} from "recharts";

import { ApiClient } from "@/lib/api";
import {
  AdminPlatformStatsOut,
  AIUsageOut,
  AIOverviewOut,
  RetrievalLogOut,
  AIEvaluationRunOut,
  AIEvaluationRunDetailOut,
  BackgroundJobOut,
  AdminUserSummaryOut,
  AdminUserJourneyDetailOut,
  ActivityEventAdminItem,
  ActivityEventAdminResponse
} from "@/types";

const COLORS = ["#818cf8", "#34d399", "#f472b6", "#fbbf24", "#38bdf8", "#a78bfa"];

export default function AdminDashboardPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<
    "overview" | "traces" | "retrieval" | "errors" | "evaluations" | "jobs" | "journeys" | "activity"
  >("overview");

  // State
  const [stats, setStats] = useState<AdminPlatformStatsOut | null>(null);
  const [overview, setOverview] = useState<AIOverviewOut | null>(null);
  const [telemetry, setTelemetry] = useState<AIUsageOut[]>([]);
  const [retrievalLogs, setRetrievalLogs] = useState<RetrievalLogOut[]>([]);
  const [errorLogs, setErrorLogs] = useState<AIUsageOut[]>([]);
  const [evalRuns, setEvalRuns] = useState<AIEvaluationRunOut[]>([]);
  const [selectedRun, setSelectedRun] = useState<AIEvaluationRunDetailOut | null>(null);
  const [jobs, setJobs] = useState<BackgroundJobOut[]>([]);
  const [inspectLog, setInspectLog] = useState<AIUsageOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);

  // PRD §16, §17: Learner Journeys & Activity Audit States
  const [adminUsers, setAdminUsers] = useState<AdminUserSummaryOut[]>([]);
  const [userSearchTerm, setUserSearchTerm] = useState("");
  const [selectedUserJourney, setSelectedUserJourney] = useState<AdminUserJourneyDetailOut | null>(null);
  const [loadingJourney, setLoadingJourney] = useState(false);

  const [activityEvents, setActivityEvents] = useState<ActivityEventAdminItem[]>([]);
  const [activityTotal, setActivityTotal] = useState(0);
  const [activityEventTypeFilter, setActivityEventTypeFilter] = useState("");
  const [activityUserFilter, setActivityUserFilter] = useState("");
  const [activityInspectPayload, setActivityInspectPayload] = useState<ActivityEventAdminItem | null>(null);
  const [loadingActivity, setLoadingActivity] = useState(false);

  // Filters
  const [featureFilter, setFeatureFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Regression Comparison State
  const [compareRunA, setCompareRunA] = useState<string>("");
  const [compareRunB, setCompareRunB] = useState<string>("");
  const [comparisonResult, setComparisonResult] = useState<any | null>(null);
  const [comparing, setComparing] = useState(false);

  useEffect(() => {
    fetchAdminData();
    fetchAdminUsers();
    fetchAdminActivities();
  }, []);

  const fetchAdminData = async () => {
    try {
      const [statsData, overviewData, telemetryData, retrievalData, errorData, evalData, jobsData] = await Promise.all([
        ApiClient.request<AdminPlatformStatsOut>("/admin/stats"),
        ApiClient.request<AIOverviewOut>("/admin/ai/overview"),
        ApiClient.request<AIUsageOut[]>("/admin/ai/usage?limit=50"),
        ApiClient.request<RetrievalLogOut[]>("/admin/ai/retrieval?limit=30"),
        ApiClient.request<AIUsageOut[]>("/admin/ai/errors?limit=30"),
        ApiClient.request<AIEvaluationRunOut[]>("/admin/ai/evaluations?limit=20"),
        ApiClient.request<BackgroundJobOut[]>("/admin/jobs?limit=20"),
      ]);

      setStats(statsData);
      setOverview(overviewData);
      setTelemetry(telemetryData);
      setRetrievalLogs(retrievalData);
      setErrorLogs(errorData);
      setEvalRuns(evalData);
      setJobs(jobsData);
    } catch (err) {
      alert("Access Denied: Administrative privileges required.");
      router.push("/dashboard");
    } finally {
      setLoading(false);
    }
  };

  const handleRunEvaluation = async (suiteType: string) => {
    setEvaluating(true);
    try {
      const newRun = await ApiClient.request<AIEvaluationRunOut>("/admin/ai/evaluations/run", {
        method: "POST",
        body: JSON.stringify({ evaluation_type: suiteType })
      });
      alert(`Evaluation run '${newRun.run_name}' completed with pass rate: ${newRun.metrics?.pass_rate}%`);
      const runs = await ApiClient.request<AIEvaluationRunOut[]>("/admin/ai/evaluations?limit=20");
      setEvalRuns(runs);
    } catch (err: any) {
      alert(`Failed to run evaluation: ${err.message || err}`);
    } finally {
      setEvaluating(false);
    }
  };

  const handleInspectRun = async (runId: string) => {
    try {
      const detail = await ApiClient.request<AIEvaluationRunDetailOut>(`/admin/ai/evaluations/${runId}`);
      setSelectedRun(detail);
    } catch (err: any) {
      alert("Failed to load run details");
    }
  };

  const handleCompareRuns = async () => {
    if (!compareRunA || !compareRunB) {
      alert("Select two runs to compare.");
      return;
    }
    setComparing(true);
    try {
      const res = await ApiClient.request(`/admin/ai/evaluations/compare?run_a=${compareRunA}&run_b=${compareRunB}`);
      setComparisonResult(res);
    } catch (err: any) {
      alert(`Comparison failed: ${err.message || err}`);
    } finally {
      setComparing(false);
    }
  };

  const fetchAdminUsers = async () => {
    try {
      const res = await ApiClient.request<AdminUserSummaryOut[]>("/admin/users");
      setAdminUsers(res);
    } catch (err) {
      console.error("Failed to load admin users:", err);
    }
  };

  const handleInspectUserJourney = async (userId: string) => {
    setLoadingJourney(true);
    try {
      const journey = await ApiClient.request<AdminUserJourneyDetailOut>(`/admin/users/${userId}/journey`);
      setSelectedUserJourney(journey);
    } catch (err: any) {
      alert(`Failed to load learner journey: ${err.message || err}`);
    } finally {
      setLoadingJourney(false);
    }
  };

  const fetchAdminActivities = async (eventType?: string, userId?: string) => {
    setLoadingActivity(true);
    try {
      let url = "/admin/activity?limit=50";
      if (eventType && eventType !== "ALL") url += `&event_type=${encodeURIComponent(eventType)}`;
      if (userId) url += `&user_id=${encodeURIComponent(userId)}`;
      const res = await ApiClient.request<ActivityEventAdminResponse>(url);
      setActivityEvents(res.items);
      setActivityTotal(res.total);
    } catch (err) {
      console.error("Failed to load activity logs:", err);
    } finally {
      setLoadingActivity(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  // Prep Recharts data
  const featureBarData = overview
    ? Object.entries(overview.requests_by_feature).map(([k, v]) => ({ feature: k, count: v }))
    : [];

  const errorPieData = overview
    ? Object.entries(overview.errors_by_type).map(([k, v]) => ({ name: k, value: v }))
    : [];

  const filteredTelemetry = telemetry.filter((t) => {
    if (featureFilter && t.feature !== featureFilter) return false;
    if (statusFilter && t.status_code !== statusFilter) return false;
    return true;
  });

  return (
    <div className="min-h-screen bg-background flex flex-col text-slate-100">
      {/* Header */}
      <header className="border-b border-gray-800 bg-surface/80 backdrop-blur sticky top-0 z-30 px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/dashboard"
            className="text-gray-400 hover:text-white p-2 rounded-lg hover:bg-surface transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider">AI Engineering Platform</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-950 text-purple-300 border border-purple-800">
                PROD OBSERVABILITY
              </span>
            </div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Shield className="w-5 h-5 text-purple-400" /> AI Observability &amp; Evaluation Center
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchAdminData}
            className="text-xs bg-surface hover:bg-surface-raised border border-gray-700 text-gray-300 hover:text-white px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh Telemetry
          </button>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="border-b border-gray-800 bg-surface/30 px-8 flex gap-2">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "overview"
              ? "border-purple-500 text-purple-400 bg-surface/50"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <BarChart3 className="w-4 h-4" /> System Overview &amp; KPIs
        </button>
        <button
          onClick={() => setActiveTab("traces")}
          className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "traces"
              ? "border-purple-500 text-purple-400 bg-surface/50"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <Cpu className="w-4 h-4" /> Live AI Traces &amp; Telemetry
        </button>
        <button
          onClick={() => setActiveTab("retrieval")}
          className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "retrieval"
              ? "border-purple-500 text-purple-400 bg-surface/50"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <Search className="w-4 h-4" /> RAG Retrieval Inspector
        </button>
        <button
          onClick={() => setActiveTab("errors")}
          className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "errors"
              ? "border-rose-500 text-rose-400 bg-surface/50"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <AlertTriangle className="w-4 h-4 text-rose-400" /> Error &amp; 429 Auditing
        </button>
        <button
          onClick={() => setActiveTab("evaluations")}
          className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "evaluations"
              ? "border-emerald-500 text-emerald-400 bg-surface/50"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Evaluation &amp; Regression Studio
        </button>
        <button
          onClick={() => setActiveTab("jobs")}
          className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "jobs"
              ? "border-blue-500 text-blue-400 bg-surface/50"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <Activity className="w-4 h-4 text-blue-400" /> Worker Health ({jobs.length})
        </button>
        <button
          onClick={() => {
            setActiveTab("journeys");
            fetchAdminUsers();
          }}
          className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "journeys"
              ? "border-cyan-500 text-cyan-400 bg-surface/50"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <Users className="w-4 h-4 text-cyan-400" /> Learner Journeys ({adminUsers.length})
        </button>
        <button
          onClick={() => {
            setActiveTab("activity");
            fetchAdminActivities(activityEventTypeFilter, activityUserFilter);
          }}
          className={`px-4 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === "activity"
              ? "border-amber-500 text-amber-400 bg-surface/50"
              : "border-transparent text-gray-400 hover:text-gray-200"
          }`}
        >
          <FileText className="w-4 h-4 text-amber-400" /> Platform Activity Audit ({activityTotal || activityEvents.length})
        </button>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 space-y-8">
        {/* TAB 1: SYSTEM OVERVIEW & KPIS */}
        {activeTab === "overview" && (
          <div className="space-y-8">
            {/* Top KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
              <div className="p-5 rounded-xl bg-surface border border-gray-800">
                <span className="text-xs font-semibold text-gray-400 uppercase">AI Requests</span>
                <div className="text-2xl font-bold text-white mt-1">{overview?.total_requests || 0}</div>
                <span className="text-[10px] text-gray-500">Total operations</span>
              </div>
              <div className="p-5 rounded-xl bg-surface border border-gray-800">
                <span className="text-xs font-semibold text-emerald-400 uppercase">Success Rate</span>
                <div className="text-2xl font-bold text-emerald-400 mt-1">{overview?.success_rate}%</div>
                <span className="text-[10px] text-gray-500">{overview?.failed_requests} failures</span>
              </div>
              <div className="p-5 rounded-xl bg-surface border border-gray-800">
                <span className="text-xs font-semibold text-blue-400 uppercase">Avg Latency</span>
                <div className="text-2xl font-bold text-blue-400 mt-1">{overview?.avg_latency_ms} ms</div>
                <span className="text-[10px] text-gray-500">Per AI completion</span>
              </div>
              <div className="p-5 rounded-xl bg-surface border border-gray-800">
                <span className="text-xs font-semibold text-indigo-400 uppercase">Total Tokens</span>
                <div className="text-2xl font-bold text-indigo-400 mt-1">{overview?.total_tokens.toLocaleString()}</div>
                <span className="text-[10px] text-gray-500">Actual provider tokens</span>
              </div>
              <div className="p-5 rounded-xl bg-surface border border-gray-800">
                <span className="text-xs font-semibold text-amber-400 uppercase">Est. Cost (USD)</span>
                <div className="text-2xl font-bold text-amber-400 mt-1">${overview?.total_estimated_cost_usd.toFixed(4)}</div>
                <span className="text-[10px] text-gray-500">Configured rates</span>
              </div>
              <div className="p-5 rounded-xl bg-surface border border-gray-800">
                <span className="text-xs font-semibold text-purple-400 uppercase">Background Workers</span>
                <div className="text-2xl font-bold text-purple-400 mt-1">{stats?.active_background_jobs} Active</div>
                <span className="text-[10px] text-rose-400">{stats?.failed_background_jobs} Failed</span>
              </div>
            </div>

            {/* Recharts Row 1: Requests & Latency Over Time */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="p-6 bg-surface border border-gray-800 rounded-xl">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-amber-400" /> Operational Latency Trend (ms)
                </h3>
                <div className="h-64">
                  {overview && overview.requests_over_time.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={overview.requests_over_time}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.5} />
                        <XAxis dataKey="time" stroke="#9ca3af" fontSize={10} />
                        <YAxis stroke="#9ca3af" fontSize={10} />
                        <Tooltip contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151", color: "#fff" }} />
                        <Line type="monotone" dataKey="latency_ms" stroke="#38bdf8" strokeWidth={2} dot={{ r: 2 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-xs text-gray-500">No time-series data yet.</div>
                  )}
                </div>
              </div>

              <div className="p-6 bg-surface border border-gray-800 rounded-xl">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-indigo-400" /> Requests by AI Feature
                </h3>
                <div className="h-64">
                  {featureBarData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={featureBarData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.5} />
                        <XAxis dataKey="feature" stroke="#9ca3af" fontSize={10} />
                        <YAxis stroke="#9ca3af" fontSize={10} />
                        <Tooltip contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151", color: "#fff" }} />
                        <Bar dataKey="count" fill="#818cf8" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-xs text-gray-500">No feature data yet.</div>
                  )}
                </div>
              </div>
            </div>

            {/* Recharts Row 2: Error Classification */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="p-6 bg-surface border border-gray-800 rounded-xl lg:col-span-1">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-400" /> Error Breakdown
                </h3>
                <div className="h-64">
                  {errorPieData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={errorPieData}
                          dataKey="value"
                          nameKey="name"
                          cx="50%"
                          cy="50%"
                          outerRadius={80}
                          label={({ name }) => name}
                        >
                          {errorPieData.map((_, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip contentStyle={{ backgroundColor: "#1f2937", borderColor: "#374151", color: "#fff" }} />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex flex-col items-center justify-center text-xs text-emerald-400">
                      <CheckCircle2 className="w-8 h-8 mb-2" />
                      Zero active failure conditions recorded.
                    </div>
                  )}
                </div>
              </div>

              {/* Models & Provider Configuration Card */}
              <div className="p-6 bg-surface border border-gray-800 rounded-xl lg:col-span-2 space-y-4">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-purple-400" /> Provider Configuration &amp; Versioning
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 bg-surface-raised rounded-lg border border-gray-700/50">
                    <span className="text-gray-400 block mb-1">Primary LLM</span>
                    <span className="font-bold text-white">Gemini 2.5 Flash</span>
                    <span className="block text-[10px] text-gray-500 mt-0.5">Google Generative API</span>
                  </div>
                  <div className="p-3 bg-surface-raised rounded-lg border border-gray-700/50">
                    <span className="text-gray-400 block mb-1">Embeddings Model</span>
                    <span className="font-bold text-white">BGE-small-en-v1.5</span>
                    <span className="block text-[10px] text-gray-500 mt-0.5">384 Dimensions (Dense)</span>
                  </div>
                  <div className="p-3 bg-surface-raised rounded-lg border border-gray-700/50">
                    <span className="text-gray-400 block mb-1">Retrieval Engine</span>
                    <span className="font-bold text-white">Hybrid (RRF Fusion)</span>
                    <span className="block text-[10px] text-gray-500 mt-0.5">HNSW Cosine + FTS</span>
                  </div>
                  <div className="p-3 bg-surface-raised rounded-lg border border-gray-700/50">
                    <span className="text-gray-400 block mb-1">Rate Limit Guard</span>
                    <span className="font-bold text-emerald-400">Bounded Backoff</span>
                    <span className="block text-[10px] text-gray-500 mt-0.5">2s / 5s / 10s + Jitter</span>
                  </div>
                  <div className="p-3 bg-surface-raised rounded-lg border border-gray-700/50">
                    <span className="text-gray-400 block mb-1">Tutor Prompt Ver.</span>
                    <span className="font-bold text-white">tutor_v1.0</span>
                    <span className="block text-[10px] text-gray-500 mt-0.5">Strict Evidence Boundary</span>
                  </div>
                  <div className="p-3 bg-surface-raised rounded-lg border border-gray-700/50">
                    <span className="text-gray-400 block mb-1">Quiz Prompt Ver.</span>
                    <span className="font-bold text-white">quiz_gen_v2.0</span>
                    <span className="block text-[10px] text-gray-500 mt-0.5">Pydantic JSON Enforced</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: LIVE AI TRACES & TELEMETRY */}
        {activeTab === "traces" && (
          <div className="bg-surface border border-gray-800 rounded-xl overflow-hidden space-y-4 p-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-purple-400" /> Correlated AI Request Traces
                </h2>
                <span className="text-xs text-gray-500">Live operational audit of all LLM and embedding calls</span>
              </div>

              {/* Filters */}
              <div className="flex items-center gap-2">
                <select
                  value={featureFilter}
                  onChange={(e) => setFeatureFilter(e.target.value)}
                  className="bg-surface-raised border border-gray-700 text-xs rounded-lg px-2.5 py-1.5 text-gray-200"
                >
                  <option value="">All Features</option>
                  <option value="TUTOR">Tutor</option>
                  <option value="QUIZ">Quiz</option>
                  <option value="ASSESSMENT">Assessment</option>
                  <option value="RECOMMENDATION">Recommendation</option>
                  <option value="DOCUMENT">Document Ingestion</option>
                </select>

                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-surface-raised border border-gray-700 text-xs rounded-lg px-2.5 py-1.5 text-gray-200"
                >
                  <option value="">All Statuses</option>
                  <option value="SUCCESS">Success</option>
                  <option value="FAILED">Failed</option>
                </select>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-gray-800 bg-surface-raised/50 text-gray-400 uppercase tracking-wider">
                    <th className="px-4 py-3 font-semibold">Request ID</th>
                    <th className="px-4 py-3 font-semibold">Feature</th>
                    <th className="px-4 py-3 font-semibold">Operation</th>
                    <th className="px-4 py-3 font-semibold">Model</th>
                    <th className="px-4 py-3 font-semibold">Tokens</th>
                    <th className="px-4 py-3 font-semibold">Latency</th>
                    <th className="px-4 py-3 font-semibold">Est. Cost</th>
                    <th className="px-4 py-3 font-semibold">Status</th>
                    <th className="px-4 py-3 font-semibold text-right">Inspect</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800 text-gray-300">
                  {filteredTelemetry.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="px-6 py-8 text-center text-gray-500">
                        No telemetry logs matched the specified filters.
                      </td>
                    </tr>
                  ) : (
                    filteredTelemetry.map((t) => (
                      <tr key={t.id} className="hover:bg-surface-raised/30 transition-colors">
                        <td className="px-4 py-3 font-mono text-[11px] text-gray-400">{t.request_id || "—"}</td>
                        <td className="px-4 py-3 font-semibold text-white">{t.feature}</td>
                        <td className="px-4 py-3 text-gray-300">{t.operation || "generate_text"}</td>
                        <td className="px-4 py-3 text-gray-400">{t.model_name}</td>
                        <td className="px-4 py-3">
                          {t.total_tokens !== null && t.total_tokens !== undefined ? t.total_tokens : <span className="text-gray-500">N/A</span>}
                        </td>
                        <td className="px-4 py-3 font-mono">{t.latency_ms} ms</td>
                        <td className="px-4 py-3 text-amber-400">
                          {t.estimated_cost_usd !== null && t.estimated_cost_usd !== undefined
                            ? `$${Number(t.estimated_cost_usd).toFixed(6)}`
                            : <span className="text-gray-500">N/A</span>}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                              t.status_code === "SUCCESS"
                                ? "bg-emerald-950 text-emerald-400 border-emerald-900"
                                : "bg-rose-950 text-rose-400 border-rose-900"
                            }`}
                          >
                            {t.status_code}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => setInspectLog(t)}
                            className="p-1 rounded bg-surface hover:bg-surface-raised border border-gray-700 text-gray-300 hover:text-white"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 3: RAG RETRIEVAL INSPECTOR */}
        {activeTab === "retrieval" && (
          <div className="bg-surface border border-gray-800 rounded-xl overflow-hidden p-6 space-y-4">
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Search className="w-4 h-4 text-purple-400" /> Project-Isolated RAG Retrieval Operations
              </h2>
              <span className="text-xs text-gray-500">
                Auditing hybrid vector + keyword retrieval candidates, similarity scores, and evidence thresholds.
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-gray-800 bg-surface-raised/50 text-gray-400 uppercase tracking-wider">
                    <th className="px-4 py-3 font-semibold">Request ID</th>
                    <th className="px-4 py-3 font-semibold">Query</th>
                    <th className="px-4 py-3 font-semibold">Method</th>
                    <th className="px-4 py-3 font-semibold">Top-K / Final</th>
                    <th className="px-4 py-3 font-semibold">Retrieval Latency</th>
                    <th className="px-4 py-3 font-semibold">Rerank Latency</th>
                    <th className="px-4 py-3 font-semibold">Evidence Grounded</th>
                    <th className="px-4 py-3 font-semibold">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800 text-gray-300">
                  {retrievalLogs.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-6 py-8 text-center text-gray-500">
                        No retrieval operations recorded yet.
                      </td>
                    </tr>
                  ) : (
                    retrievalLogs.map((r) => (
                      <tr key={r.id} className="hover:bg-surface-raised/30 transition-colors">
                        <td className="px-4 py-3 font-mono text-[11px] text-purple-400">{r.request_id}</td>
                        <td className="px-4 py-3 font-medium text-white max-w-xs truncate">{r.query}</td>
                        <td className="px-4 py-3 text-gray-400">{r.retrieval_method}</td>
                        <td className="px-4 py-3 font-mono">{r.top_k} / {r.final_k}</td>
                        <td className="px-4 py-3 font-mono">{r.retrieval_latency_ms} ms</td>
                        <td className="px-4 py-3 font-mono">{r.reranking_latency_ms} ms</td>
                        <td className="px-4 py-3">
                          {r.has_sufficient_evidence ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-900 flex items-center w-fit gap-1">
                              <CheckCircle2 className="w-3 h-3" /> Grounded
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-400 border border-amber-900 flex items-center w-fit gap-1">
                              <AlertCircle className="w-3 h-3" /> Refused
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-gray-500 font-mono text-[11px]">
                          {new Date(r.created_at).toLocaleTimeString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 4: ERROR & 429 RATE-LIMIT AUDITING */}
        {activeTab === "errors" && (
          <div className="bg-surface border border-gray-800 rounded-xl overflow-hidden p-6 space-y-4">
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400" /> AI Failures &amp; Rate-Limit Classification
              </h2>
              <span className="text-xs text-gray-500">
                Detailed telemetry for HTTP 429 quota exhaustion, timeouts, and structured parsing failures.
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-gray-800 bg-surface-raised/50 text-gray-400 uppercase tracking-wider">
                    <th className="px-4 py-3 font-semibold">Timestamp</th>
                    <th className="px-4 py-3 font-semibold">Feature</th>
                    <th className="px-4 py-3 font-semibold">Operation</th>
                    <th className="px-4 py-3 font-semibold">Error Type</th>
                    <th className="px-4 py-3 font-semibold">Sanitized Error Message</th>
                    <th className="px-4 py-3 font-semibold">Request ID</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800 text-gray-300">
                  {errorLogs.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-8 text-center text-emerald-400">
                        <CheckCircle2 className="w-6 h-6 mx-auto mb-1" />
                        No active error traces recorded. The AI system is operating normally.
                      </td>
                    </tr>
                  ) : (
                    errorLogs.map((err) => (
                      <tr key={err.id} className="hover:bg-surface-raised/30 transition-colors">
                        <td className="px-4 py-3 font-mono text-[11px] text-gray-400">
                          {new Date(err.created_at).toLocaleTimeString()}
                        </td>
                        <td className="px-4 py-3 font-semibold text-white">{err.feature}</td>
                        <td className="px-4 py-3 text-gray-300">{err.operation || "generate"}</td>
                        <td className="px-4 py-3">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-300 border border-rose-800">
                            {err.error_type || "UNKNOWN_ERROR"}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-rose-300 font-mono text-[11px] max-w-md truncate">
                          {err.error_details || "AI service temporarily unavailable."}
                        </td>
                        <td className="px-4 py-3 font-mono text-[11px] text-gray-500">{err.request_id || "—"}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 5: EVALUATION & REGRESSION BENCHMARK STUDIO */}
        {activeTab === "evaluations" && (
          <div className="space-y-6">
            {/* Top Run Controls */}
            <div className="p-6 bg-surface border border-gray-800 rounded-xl flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Automated AI Evaluation &amp; Regression Benchmarks
                </h2>
                <span className="text-xs text-gray-400">
                  Execute curated test datasets to assess Groundedness, Citation Integrity, Recall@5, MRR, and Schema reliability.
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={() => handleRunEvaluation("FULL_SUITE")}
                  disabled={evaluating}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-4 py-2 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
                >
                  <Play className="w-3.5 h-3.5" /> {evaluating ? "Evaluating..." : "Run Full Benchmark Suite"}
                </button>
                <button
                  onClick={() => handleRunEvaluation("TUTOR")}
                  disabled={evaluating}
                  className="bg-surface-raised hover:bg-surface border border-gray-700 text-xs px-3 py-2 rounded-lg transition-colors"
                >
                  Run Tutor Evs
                </button>
                <button
                  onClick={() => handleRunEvaluation("RETRIEVAL")}
                  disabled={evaluating}
                  className="bg-surface-raised hover:bg-surface border border-gray-700 text-xs px-3 py-2 rounded-lg transition-colors"
                >
                  Run Retrieval Evs
                </button>
              </div>
            </div>

            {/* Regression Comparator Box */}
            <div className="p-5 bg-surface-raised/40 border border-gray-800 rounded-xl space-y-4">
              <div className="flex items-center gap-2 text-xs font-bold text-purple-400 uppercase">
                <GitCompare className="w-4 h-4" /> Compare Evaluation Runs for Regressions
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <select
                  value={compareRunA}
                  onChange={(e) => setCompareRunA(e.target.value)}
                  className="bg-surface border border-gray-700 text-xs rounded-lg px-3 py-2 text-gray-200"
                >
                  <option value="">Select Baseline Run (Run A)</option>
                  {evalRuns.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.run_name} ({r.metrics?.pass_rate}%)
                    </option>
                  ))}
                </select>

                <span className="text-gray-500 text-xs">vs</span>

                <select
                  value={compareRunB}
                  onChange={(e) => setCompareRunB(e.target.value)}
                  className="bg-surface border border-gray-700 text-xs rounded-lg px-3 py-2 text-gray-200"
                >
                  <option value="">Select Target Run (Run B)</option>
                  {evalRuns.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.run_name} ({r.metrics?.pass_rate}%)
                    </option>
                  ))}
                </select>

                <button
                  onClick={handleCompareRuns}
                  disabled={comparing || !compareRunA || !compareRunB}
                  className="bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
                >
                  {comparing ? "Comparing..." : "Detect Regressions"}
                </button>
              </div>

              {/* Comparison Output */}
              {comparisonResult && (
                <div className="p-4 rounded-lg bg-surface border border-gray-700 text-xs space-y-3 mt-3">
                  <div className="flex items-center justify-between border-b border-gray-800 pb-2">
                    <span className="font-bold text-white">Regression Comparison Results</span>
                    {comparisonResult.has_regression ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-400 border border-rose-800">
                        Regression Detected ({comparisonResult.regressed_cases?.length} cases)
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
                        Zero Regressions Detected
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {Object.entries(comparisonResult.metrics_diff || {}).map(([metric, data]: any) => (
                      <div key={metric} className="p-2.5 rounded bg-surface-raised border border-gray-800">
                        <span className="text-gray-400 text-[10px] block">{metric}</span>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="font-bold text-white">{data.target}</span>
                          <span
                            className={`text-[10px] font-bold ${
                              data.delta >= 0 ? "text-emerald-400" : "text-rose-400"
                            }`}
                          >
                            {data.delta >= 0 ? `+${data.delta}` : data.delta}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* List of Evaluation Runs */}
            <div className="bg-surface border border-gray-800 rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-800">
                <h3 className="text-xs font-bold text-white uppercase tracking-wider">Evaluation Run History</h3>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-gray-800 bg-surface-raised/50 text-gray-400 uppercase tracking-wider">
                      <th className="px-4 py-3 font-semibold">Run Name</th>
                      <th className="px-4 py-3 font-semibold">Suite</th>
                      <th className="px-4 py-3 font-semibold">Model</th>
                      <th className="px-4 py-3 font-semibold">Pass Rate</th>
                      <th className="px-4 py-3 font-semibold">Cases (Pass/Fail)</th>
                      <th className="px-4 py-3 font-semibold">Groundedness</th>
                      <th className="px-4 py-3 font-semibold">Recall@5</th>
                      <th className="px-4 py-3 font-semibold">Timestamp</th>
                      <th className="px-4 py-3 font-semibold text-right">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800 text-gray-300">
                    {evalRuns.length === 0 ? (
                      <tr>
                        <td colSpan={9} className="px-6 py-8 text-center text-gray-500">
                          No evaluation runs found. Click 'Run Full Benchmark Suite' to execute.
                        </td>
                      </tr>
                    ) : (
                      evalRuns.map((r) => (
                        <tr key={r.id} className="hover:bg-surface-raised/30 transition-colors">
                          <td className="px-4 py-3 font-semibold text-white">{r.run_name}</td>
                          <td className="px-4 py-3">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-950 text-purple-300 border border-purple-800">
                              {r.evaluation_type}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-gray-400">{r.model}</td>
                          <td className="px-4 py-3 font-bold text-emerald-400">
                            {r.metrics?.pass_rate !== undefined ? `${r.metrics.pass_rate}%` : "—"}
                          </td>
                          <td className="px-4 py-3 font-mono">
                            <span className="text-emerald-400">{r.passed_cases}</span> /{" "}
                            <span className="text-rose-400">{r.failed_cases}</span> (Total {r.total_cases})
                          </td>
                          <td className="px-4 py-3 font-mono text-indigo-400">
                            {r.metrics?.tutor_groundedness ? (r.metrics.tutor_groundedness * 100).toFixed(1) + "%" : "—"}
                          </td>
                          <td className="px-4 py-3 font-mono text-blue-400">
                            {r.metrics?.retrieval_recall_at_5 ? (r.metrics.retrieval_recall_at_5 * 100).toFixed(1) + "%" : "—"}
                          </td>
                          <td className="px-4 py-3 text-gray-500 font-mono text-[11px]">
                            {new Date(r.created_at).toLocaleTimeString()}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <button
                              onClick={() => handleInspectRun(r.id)}
                              className="px-2.5 py-1 rounded bg-surface hover:bg-surface-raised border border-gray-700 text-xs text-gray-200"
                            >
                              Inspect Cases
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Granular Case Modal / Drawer */}
            {selectedRun && (
              <div className="p-6 bg-surface border border-purple-500/50 rounded-xl space-y-4">
                <div className="flex items-center justify-between border-b border-gray-800 pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-white">
                      Granular Cases for: {selectedRun.run_name}
                    </h3>
                    <span className="text-xs text-gray-400">
                      {selectedRun.passed_cases} passed, {selectedRun.failed_cases} failed
                    </span>
                  </div>
                  <button
                    onClick={() => setSelectedRun(null)}
                    className="text-xs text-gray-400 hover:text-white px-2 py-1 rounded bg-surface-raised border border-gray-700"
                  >
                    Close
                  </button>
                </div>

                <div className="max-h-96 overflow-y-auto space-y-2">
                  {selectedRun.results?.map((res) => (
                    <div
                      key={res.id}
                      className={`p-3 rounded-lg border text-xs flex items-start justify-between gap-4 ${
                        res.passed ? "bg-surface-raised/40 border-gray-800" : "bg-rose-950/20 border-rose-900/50"
                      }`}
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-purple-400">{res.case_id}</span>
                          <span className="text-gray-400">[{res.feature}]</span>
                          {res.passed ? (
                            <span className="text-emerald-400 font-bold flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" /> PASS
                            </span>
                          ) : (
                            <span className="text-rose-400 font-bold flex items-center gap-1">
                              <XCircle className="w-3 h-3" /> FAIL
                            </span>
                          )}
                        </div>
                        {res.failure_reason && (
                          <p className="text-rose-300 font-mono text-[11px]">{res.failure_reason}</p>
                        )}
                      </div>
                      <span className="font-bold text-white font-mono">Score: {Number(res.score).toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 6: BACKGROUND WORKER HEALTH */}
        {activeTab === "jobs" && (
          <div className="bg-surface border border-gray-800 rounded-xl overflow-hidden p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Activity className="w-4 h-4 text-blue-400" /> Background Worker Queue Health
                </h2>
                <span className="text-xs text-gray-500">
                  Tracking Celery asynchronous task states, attempts, and idempotent deduplication keys.
                </span>
              </div>
            </div>

            <div className="space-y-3">
              {jobs.length === 0 ? (
                <p className="text-center py-6 text-gray-500 text-xs">
                  All background workers are idle and healthy.
                </p>
              ) : (
                jobs.map((j) => (
                  <div
                    key={j.id}
                    className="p-3.5 rounded-lg bg-surface-raised border border-gray-700/50 flex items-center justify-between text-xs"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white">{j.job_type}</span>
                        <span className="text-gray-500 text-[11px] font-mono">Key: {j.idempotency_key}</span>
                      </div>
                      {j.last_error && <p className="text-rose-400 text-[11px] mt-1 font-mono">{j.last_error}</p>}
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-gray-400 text-[11px]">Attempts: {j.attempts}</span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                          j.status === "COMPLETED"
                            ? "bg-emerald-950 text-emerald-400 border-emerald-900"
                            : j.status === "FAILED"
                            ? "bg-rose-950 text-rose-400 border-rose-900"
                            : "bg-blue-950 text-blue-400 border-blue-900"
                        }`}
                      >
                        {j.status}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* TAB 7: LEARNER JOURNEYS (PRD §16, §17) */}
        {activeTab === "journeys" && (
          <div className="space-y-6">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-surface p-6 rounded-xl border border-gray-800">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Users className="w-5 h-5 text-cyan-400" /> Platform Learner Directory &amp; Journeys
                </h2>
                <p className="text-xs text-gray-400 mt-1">
                  Inspect individual student learning trajectories, concept mastery profiles, quiz attempts, and AI usage.
                </p>
              </div>
              <div className="flex items-center gap-3 w-full md:w-auto">
                <div className="relative flex-1 md:w-64">
                  <Search className="w-4 h-4 absolute left-3 top-2.5 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search by name or email..."
                    value={userSearchTerm}
                    onChange={(e) => setUserSearchTerm(e.target.value)}
                    className="w-full bg-surface-raised border border-gray-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <button
                  onClick={fetchAdminUsers}
                  className="px-3 py-1.5 rounded-lg bg-surface-raised hover:bg-gray-800 border border-gray-700 text-xs text-gray-300 hover:text-white flex items-center gap-1.5 transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Refresh
                </button>
              </div>
            </div>

            {/* Learners Table */}
            <div className="bg-surface border border-gray-800 rounded-xl overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-gray-300">
                  <thead className="bg-surface-raised/80 text-gray-400 uppercase text-[10px] font-semibold tracking-wider border-b border-gray-800">
                    <tr>
                      <th className="py-3 px-6">Learner</th>
                      <th className="py-3 px-4">Spaces / Projects</th>
                      <th className="py-3 px-4">Quizzes</th>
                      <th className="py-3 px-4">Avg Mastery</th>
                      <th className="py-3 px-4">AI Spend</th>
                      <th className="py-3 px-4">Joined</th>
                      <th className="py-3 px-6 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800">
                    {adminUsers
                      .filter((u) =>
                        u.full_name.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
                        u.email.toLowerCase().includes(userSearchTerm.toLowerCase())
                      )
                      .map((u) => (
                        <tr key={u.id} className="hover:bg-surface-raised/50 transition-colors">
                          <td className="py-4 px-6">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-full bg-cyan-950 border border-cyan-800 text-cyan-400 flex items-center justify-center font-bold text-xs uppercase">
                                {u.full_name.charAt(0) || u.email.charAt(0)}
                              </div>
                              <div>
                                <div className="font-semibold text-white">{u.full_name}</div>
                                <div className="text-[11px] text-gray-400">{u.email}</div>
                                <div className="flex items-center gap-1 mt-0.5">
                                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-300 border border-gray-700">
                                    {u.role}
                                  </span>
                                  {u.is_active && (
                                    <span className="text-[9px] text-emerald-400 flex items-center gap-0.5">
                                      &bull; Active
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td className="py-4 px-4 font-medium text-white">
                            {u.spaces_count} spaces &bull; {u.projects_count} projects
                          </td>
                          <td className="py-4 px-4 font-medium text-white">
                            {u.quizzes_taken} completed
                          </td>
                          <td className="py-4 px-4">
                            <div className="flex items-center gap-2">
                              <div className="w-20 bg-gray-800 rounded-full h-2 overflow-hidden border border-gray-700">
                                <div
                                  className={`h-full rounded-full ${
                                    u.average_mastery >= 75
                                      ? "bg-emerald-500"
                                      : u.average_mastery >= 45
                                      ? "bg-amber-500"
                                      : "bg-cyan-500"
                                  }`}
                                  style={{ width: `${Math.min(100, Math.max(5, u.average_mastery))}%` }}
                                />
                              </div>
                              <span className="font-bold text-white">{u.average_mastery}%</span>
                            </div>
                          </td>
                          <td className="py-4 px-4">
                            <div className="font-mono text-emerald-400 font-semibold">${u.total_ai_cost.toFixed(4)}</div>
                            <div className="text-[10px] text-gray-500 font-mono">{u.total_ai_tokens.toLocaleString()} tokens</div>
                          </td>
                          <td className="py-4 px-4 text-gray-400">
                            {new Date(u.created_at).toLocaleDateString()}
                          </td>
                          <td className="py-4 px-6 text-right">
                            <button
                              onClick={() => handleInspectUserJourney(u.id)}
                              className="px-3 py-1.5 rounded-lg bg-cyan-950/80 hover:bg-cyan-900 border border-cyan-800 text-cyan-300 text-xs font-medium transition-colors shadow-sm"
                            >
                              Inspect Journey &rarr;
                            </button>
                          </td>
                        </tr>
                      ))}
                    {adminUsers.length === 0 && (
                      <tr>
                        <td colSpan={7} className="py-8 text-center text-gray-500">
                          No registered learners found.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 8: PLATFORM ACTIVITY AUDIT LOG (PRD §16, §17) */}
        {activeTab === "activity" && (
          <div className="space-y-6">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-surface p-6 rounded-xl border border-gray-800">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <FileText className="w-5 h-5 text-amber-400" /> Platform Multi-Parameter Activity Log
                </h2>
                <p className="text-xs text-gray-400 mt-1">
                  Chronological platform audit trail filterable by event type and user ID across all spaces and projects.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                {/* Event Type Filter */}
                <select
                  value={activityEventTypeFilter}
                  onChange={(e) => {
                    setActivityEventTypeFilter(e.target.value);
                    fetchAdminActivities(e.target.value, activityUserFilter);
                  }}
                  className="bg-surface-raised border border-gray-700 text-xs text-white rounded-lg px-3 py-1.5 focus:outline-none focus:border-amber-500"
                >
                  <option value="ALL">All Event Types</option>
                  <option value="QUIZ_COMPLETED">QUIZ_COMPLETED</option>
                  <option value="TUTOR_INTERACTION">TUTOR_INTERACTION</option>
                  <option value="MATERIAL_UPLOADED">MATERIAL_UPLOADED</option>
                  <option value="MATERIAL_PROCESSED">MATERIAL_PROCESSED</option>
                  <option value="REPEATED_MISTAKE_DIAGNOSED">REPEATED_MISTAKE_DIAGNOSED</option>
                  <option value="PROJECT_CREATED">PROJECT_CREATED</option>
                  <option value="MASTERY_UPDATED">MASTERY_UPDATED</option>
                </select>

                <button
                  onClick={() => fetchAdminActivities(activityEventTypeFilter, activityUserFilter)}
                  disabled={loadingActivity}
                  className="px-3 py-1.5 rounded-lg bg-surface-raised hover:bg-gray-800 border border-gray-700 text-xs text-gray-300 hover:text-white flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingActivity ? "animate-spin" : ""}`} /> Refresh Feed
                </button>
              </div>
            </div>

            {/* Activity Table */}
            <div className="bg-surface border border-gray-800 rounded-xl overflow-hidden shadow-xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-gray-300">
                  <thead className="bg-surface-raised/80 text-gray-400 uppercase text-[10px] font-semibold tracking-wider border-b border-gray-800">
                    <tr>
                      <th className="py-3 px-6">Timestamp</th>
                      <th className="py-3 px-4">Event Type</th>
                      <th className="py-3 px-4">Learner</th>
                      <th className="py-3 px-4">Project</th>
                      <th className="py-3 px-4">Payload Summary</th>
                      <th className="py-3 px-6 text-right">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800">
                    {activityEvents.map((ev) => (
                      <tr key={ev.id} className="hover:bg-surface-raised/50 transition-colors">
                        <td className="py-3.5 px-6 font-mono text-gray-400 whitespace-nowrap">
                          {new Date(ev.created_at).toLocaleString()}
                        </td>
                        <td className="py-3.5 px-4">
                          <span
                            className={`px-2.5 py-1 rounded-full text-[10px] font-bold border ${
                              ev.event_type === "QUIZ_COMPLETED"
                                ? "bg-emerald-950/80 text-emerald-400 border-emerald-800"
                                : ev.event_type === "TUTOR_INTERACTION"
                                ? "bg-blue-950/80 text-blue-400 border-blue-800"
                                : ev.event_type === "REPEATED_MISTAKE_DIAGNOSED"
                                ? "bg-rose-950/80 text-rose-400 border-rose-800"
                                : ev.event_type === "MATERIAL_PROCESSED"
                                ? "bg-purple-950/80 text-purple-400 border-purple-800"
                                : "bg-amber-950/80 text-amber-400 border-amber-800"
                            }`}
                          >
                            {ev.event_type}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 font-medium text-white">
                          {ev.user_email || ev.user_id.slice(0, 8)}
                        </td>
                        <td className="py-3.5 px-4 text-gray-300">
                          {ev.project_name || "—"}
                        </td>
                        <td className="py-3.5 px-4 font-mono text-[11px] text-gray-400 max-w-xs truncate">
                          {JSON.stringify(ev.payload)}
                        </td>
                        <td className="py-3.5 px-6 text-right">
                          <button
                            onClick={() => setActivityInspectPayload(ev)}
                            className="px-2.5 py-1 rounded bg-surface hover:bg-surface-raised border border-gray-700 text-gray-300 hover:text-white text-[11px] transition-colors"
                          >
                            Inspect JSON
                          </button>
                        </td>
                      </tr>
                    ))}
                    {activityEvents.length === 0 && (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-gray-500">
                          No activity events recorded yet matching this filter.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Inspect Log Modal */}
      {inspectLog && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-surface border border-gray-700 rounded-xl max-w-2xl w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto text-xs">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Eye className="w-4 h-4 text-purple-400" /> AI Request Trace Inspector
              </h3>
              <button onClick={() => setInspectLog(null)} className="text-gray-400 hover:text-white font-bold">
                ✕
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="text-gray-400 block">Request ID</span>
                <span className="font-mono text-purple-400 font-bold">{inspectLog.request_id || "—"}</span>
              </div>
              <div>
                <span className="text-gray-400 block">Feature / Operation</span>
                <span className="font-semibold text-white">{inspectLog.feature} — {inspectLog.operation}</span>
              </div>
              <div>
                <span className="text-gray-400 block">Model &amp; Provider</span>
                <span className="text-gray-200">{inspectLog.model_name} ({inspectLog.provider || "gemini"})</span>
              </div>
              <div>
                <span className="text-gray-400 block">Latency</span>
                <span className="font-mono text-blue-400">{inspectLog.latency_ms} ms</span>
              </div>
              <div>
                <span className="text-gray-400 block">Tokens (In / Out / Total)</span>
                <span className="font-mono text-gray-200">
                  {inspectLog.prompt_tokens ?? "N/A"} / {inspectLog.completion_tokens ?? "N/A"} / {inspectLog.total_tokens ?? "N/A"}
                </span>
              </div>
              <div>
                <span className="text-gray-400 block">Estimated Cost</span>
                <span className="font-mono text-emerald-400">
                  {inspectLog.estimated_cost_usd !== null ? `$${Number(inspectLog.estimated_cost_usd).toFixed(6)}` : "N/A"}
                </span>
              </div>
            </div>

            {inspectLog.metadata_json && (
              <div>
                <span className="text-gray-400 block mb-1">Attached Metadata</span>
                <pre className="p-3 rounded-lg bg-surface-raised text-gray-300 font-mono text-[11px] overflow-x-auto">
                  {JSON.stringify(inspectLog.metadata_json, null, 2)}
                </pre>
              </div>
            )}

            {inspectLog.error_details && (
              <div>
                <span className="text-rose-400 block mb-1">Error Trace</span>
                <pre className="p-3 rounded-lg bg-rose-950/30 border border-rose-900/50 text-rose-300 font-mono text-[11px] overflow-x-auto">
                  {inspectLog.error_details}
                </pre>
              </div>
            )}

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setInspectLog(null)}
                className="px-4 py-1.5 rounded-lg bg-surface-raised hover:bg-surface border border-gray-700 text-white"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Learner Journey Inspector Modal (PRD §16, §17) */}
      {selectedUserJourney && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-surface border border-gray-800 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6 sm:p-8 space-y-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-800 pb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-cyan-950 border border-cyan-800 text-cyan-400 flex items-center justify-center font-bold text-sm uppercase">
                  {selectedUserJourney.user.full_name.charAt(0)}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider">Learner Journey Drill-Down</span>
                    <span className="text-[10px] bg-gray-800 border border-gray-700 text-gray-300 px-2 py-0.5 rounded-full font-medium">
                      {selectedUserJourney.user.role}
                    </span>
                  </div>
                  <h2 className="text-lg font-bold text-white">{selectedUserJourney.user.full_name}</h2>
                  <p className="text-xs text-gray-400">{selectedUserJourney.user.email}</p>
                </div>
              </div>

              <button
                onClick={() => setSelectedUserJourney(null)}
                className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Quick Metrics Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-surface-raised border border-gray-700/50">
                <span className="text-gray-400">Total Projects</span>
                <div className="text-lg font-bold text-white mt-1">{selectedUserJourney.projects.length}</div>
              </div>
              <div className="p-3 rounded-xl bg-surface-raised border border-gray-700/50">
                <span className="text-gray-400">Quizzes Completed</span>
                <div className="text-lg font-bold text-white mt-1">{selectedUserJourney.quiz_history.length}</div>
              </div>
              <div className="p-3 rounded-xl bg-surface-raised border border-gray-700/50">
                <span className="text-gray-400">Total AI Tokens</span>
                <div className="text-lg font-bold text-cyan-400 mt-1 font-mono">
                  {selectedUserJourney.ai_usage.total_tokens.toLocaleString()}
                </div>
              </div>
              <div className="p-3 rounded-xl bg-surface-raised border border-gray-700/50">
                <span className="text-gray-400">Total AI Cost</span>
                <div className="text-lg font-bold text-emerald-400 mt-1 font-mono">
                  ${selectedUserJourney.ai_usage.total_cost_usd.toFixed(4)}
                </div>
              </div>
            </div>

            {/* Diagnosed Misconceptions (PRD §11 & §14) */}
            {selectedUserJourney.diagnosed_misconceptions.length > 0 && (
              <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-800/80 space-y-2">
                <div className="text-xs font-bold uppercase tracking-wider text-rose-400 flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4" /> Diagnosed Cognitive Misconceptions (PRD §11 &amp; §14)
                </div>
                <div className="space-y-2">
                  {selectedUserJourney.diagnosed_misconceptions.map((dm, idx) => (
                    <div key={idx} className="p-2.5 rounded-lg bg-rose-900/20 border border-rose-800/40 text-xs text-rose-200">
                      <div className="font-semibold text-rose-300">{dm.concept || "Struggling Concept"}</div>
                      <p className="text-[11px] text-rose-100 mt-0.5">{dm.diagnosis || dm.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Concept Mastery Breakdown */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3 flex items-center gap-1.5">
                <BarChart3 className="w-3.5 h-3.5 text-cyan-400" /> Concept Mastery Trajectory
              </h3>
              {selectedUserJourney.mastery_breakdown.length === 0 ? (
                <p className="text-xs text-gray-500 italic">No concept mastery records logged for this learner yet.</p>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {selectedUserJourney.mastery_breakdown.map((cm) => (
                    <div key={cm.concept_id} className="p-3.5 rounded-xl bg-surface-raised border border-gray-700/60 text-xs">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-bold text-white truncate max-w-[200px]">{cm.concept_name}</span>
                        <span className="font-mono font-bold text-cyan-400">{cm.mastery_score}%</span>
                      </div>
                      <div className="w-full bg-gray-800 rounded-full h-1.5 overflow-hidden mb-2">
                        <div
                          className={`h-full rounded-full ${
                            cm.mastery_score >= 75 ? "bg-emerald-500" : cm.mastery_score >= 45 ? "bg-amber-500" : "bg-rose-500"
                          }`}
                          style={{ width: `${Math.min(100, Math.max(5, cm.mastery_score))}%` }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-[11px] text-gray-400">
                        <span className="px-1.5 py-0.5 rounded bg-gray-800 text-[10px] text-cyan-300 border border-gray-700">
                          {cm.growth_state}
                        </span>
                        <span>{cm.total_attempts} attempts &bull; {cm.consecutive_mistakes} errors</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Quiz History Timeline */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3 flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5 text-indigo-400" /> Assessment History
              </h3>
              {selectedUserJourney.quiz_history.length === 0 ? (
                <p className="text-xs text-gray-500 italic">No quizzes completed yet.</p>
              ) : (
                <div className="divide-y divide-gray-800 border border-gray-800 rounded-xl overflow-hidden bg-surface-raised/40">
                  {selectedUserJourney.quiz_history.map((q) => (
                    <div key={q.id} className="px-4 py-3 flex items-center justify-between text-xs">
                      <div>
                        <div className="font-semibold text-white">{q.title}</div>
                        <div className="text-[10px] text-gray-500">{new Date(q.created_at).toLocaleString()}</div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-gray-800 text-gray-300">
                          {q.status}
                        </span>
                        <span className={`font-bold font-mono ${q.score >= 70 ? "text-emerald-400" : "text-amber-400"}`}>
                          {q.score}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setSelectedUserJourney(null)}
                className="px-4 py-1.5 rounded-lg bg-surface-raised hover:bg-gray-800 border border-gray-700 text-xs text-white transition-colors"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Activity JSON Payload Inspector Modal */}
      {activityInspectPayload && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-surface border border-gray-700 rounded-xl max-w-xl w-full p-6 space-y-4 max-h-[85vh] overflow-y-auto text-xs shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <FileText className="w-4 h-4 text-amber-400" /> Activity Event Payload Inspector
              </h3>
              <button onClick={() => setActivityInspectPayload(null)} className="text-gray-400 hover:text-white font-bold">
                ✕
              </button>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-gray-400">
                <span>Event Type: <strong className="text-amber-400">{activityInspectPayload.event_type}</strong></span>
                <span>{new Date(activityInspectPayload.created_at).toLocaleString()}</span>
              </div>
              <pre className="p-3.5 rounded-xl bg-surface-raised border border-gray-800 text-gray-200 font-mono text-[11px] overflow-x-auto">
                {JSON.stringify(activityInspectPayload.payload, null, 2)}
              </pre>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setActivityInspectPayload(null)}
                className="px-4 py-1.5 rounded-lg bg-surface-raised hover:bg-gray-800 border border-gray-700 text-xs text-white"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
