"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Brain,
  Sparkles,
  Folder,
  ArrowRight,
  BookOpen,
  AlertTriangle,
  CheckCircle,
  Plus,
  LogOut,
  Shield,
  Award,
  Flame,
  BarChart3,
  TrendingUp,
  Clock,
  FileText
} from "lucide-react";
import { ApiClient } from "@/lib/api";
import { Space, Project, GlobalAnalyticsOut } from "@/types";

export default function DashboardPage() {
  const router = useRouter();
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [globalAnalytics, setGlobalAnalytics] = useState<GlobalAnalyticsOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);
  const [showCreateSpace, setShowCreateSpace] = useState(false);
  const [spaceName, setSpaceName] = useState("");
  const [spaceDesc, setSpaceDesc] = useState("");

  useEffect(() => {
    fetchUserData();
  }, []);

  const fetchUserData = async () => {
    try {
      const userData = await ApiClient.request<any>("/auth/me");
      setUser(userData);
      const spacesData = await ApiClient.request<Space[]>("/spaces");
      setSpaces(spacesData);

      try {
        const analyticsData = await ApiClient.request<GlobalAnalyticsOut>("/analytics/global");
        setGlobalAnalytics(analyticsData);
      } catch (err) {
        console.warn("Global analytics fetch skipped or error:", err);
      }
    } catch (err) {
      router.push("/login");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSpace = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await ApiClient.request("/spaces", {
        method: "POST",
        body: JSON.stringify({ name: spaceName, description: spaceDesc }),
      });
      setSpaceName("");
      setSpaceDesc("");
      setShowCreateSpace(false);
      fetchUserData();
    } catch (err: any) {
      alert(err.message || "Failed to create space");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("study_companion_token");
    router.push("/login");
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-500"></div>
          <p className="text-sm text-gray-400">Loading your learning workspace...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Top Navbar */}
      <header className="border-b border-gray-800 bg-surface/50 backdrop-blur px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-primary-600 p-2 rounded-lg text-white shadow-lg shadow-blue-500/20">
            <Brain className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-white">AI Study Companion</h1>
            <p className="text-xs text-gray-400">Persistent &amp; Measurable Learning Workspace</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {user?.role === "ADMIN" && (
            <Link
              href="/admin"
              className="text-xs font-semibold uppercase tracking-wider bg-purple-950/80 hover:bg-purple-900 border border-purple-800 text-purple-300 px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors"
            >
              <Shield className="w-3.5 h-3.5" /> Admin Portal
            </Link>
          )}
          <span className="text-sm text-gray-300 font-medium">{user?.full_name}</span>
          <button
            onClick={handleLogout}
            className="text-gray-400 hover:text-white p-2 rounded-lg hover:bg-surface transition-colors"
            title="Sign Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        {/* Core Question 1 & 3 Hero: Continue Learning & What should I do next */}
        <div className="mb-10 p-6 rounded-2xl bg-gradient-to-r from-blue-950/40 via-surface to-surface border border-blue-900/50 shadow-xl relative overflow-hidden">
          <div className="relative z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-900/60 border border-blue-700 text-blue-300 text-xs font-semibold uppercase tracking-wider mb-3">
              <Sparkles className="w-3.5 h-3.5" /> Recommended Next Action
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-white mb-2">
              Reinforce Neural Optimization Fundamentals
            </h2>
            <p className="text-sm text-gray-300 max-w-2xl mb-6">
              Your concept mastery on &ldquo;Vanishing Gradients&rdquo; is at 42% with 2 consecutive mistakes. Review Page 14 of your study materials and complete a short adaptive assessment.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              {spaces.length > 0 && (
                <Link
                  href={`/spaces/${spaces[0].id}`}
                  className="bg-primary-600 hover:bg-primary-500 text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-colors flex items-center gap-2 shadow-lg shadow-blue-500/20"
                >
                  Continue Learning <ArrowRight className="w-4 h-4" />
                </Link>
              )}
            </div>
          </div>
        </div>

        {/* Global Analytics Overview Cards */}
        {globalAnalytics && (
          <div className="mb-10">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-cyan-400" /> Platform-Wide Learning Analytics
                </h3>
                <p className="text-xs text-gray-400">Aggregated performance across all spaces &amp; learning journeys</p>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-surface border border-gray-800 flex items-center gap-3">
                <span className="p-2.5 rounded-lg bg-emerald-950/80 border border-emerald-800 text-emerald-400">
                  <Award className="w-5 h-5" />
                </span>
                <div>
                  <div className="text-xl font-bold text-white">{globalAnalytics.overview.platform_average_mastery}%</div>
                  <div className="text-[11px] text-gray-400">Platform Mastery</div>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-surface border border-gray-800 flex items-center gap-3">
                <span className="p-2.5 rounded-lg bg-amber-950/80 border border-amber-800 text-amber-400">
                  <Flame className="w-5 h-5" />
                </span>
                <div>
                  <div className="text-xl font-bold text-white">{globalAnalytics.overview.streak_days} Days</div>
                  <div className="text-[11px] text-gray-400">Active Streak</div>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-surface border border-gray-800 flex items-center gap-3">
                <span className="p-2.5 rounded-lg bg-blue-950/80 border border-blue-800 text-blue-400">
                  <Sparkles className="w-5 h-5" />
                </span>
                <div>
                  <div className="text-xl font-bold text-white">{globalAnalytics.overview.total_quizzes_completed}</div>
                  <div className="text-[11px] text-gray-400">Quizzes Evaluated</div>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-surface border border-gray-800 flex items-center gap-3">
                <span className="p-2.5 rounded-lg bg-cyan-950/80 border border-cyan-800 text-cyan-400">
                  <CheckCircle className="w-5 h-5" />
                </span>
                <div>
                  <div className="text-xl font-bold text-white">{globalAnalytics.overview.overall_accuracy_rate}%</div>
                  <div className="text-[11px] text-gray-400">Question Accuracy</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Section Header: Spaces */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-white">Your Learning Spaces</h2>
            <p className="text-xs text-gray-400">Broad knowledge areas containing focused project journeys</p>
          </div>
          <button
            onClick={() => setShowCreateSpace(true)}
            className="bg-surface hover:bg-surface-raised border border-gray-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> Create Space
          </button>
        </div>

        {/* Spaces Grid */}
        {spaces.length === 0 ? (
          <div className="p-12 text-center rounded-2xl bg-surface border border-gray-800">
            <Folder className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-white mb-2">No learning spaces created yet</h3>
            <p className="text-sm text-gray-400 max-w-md mx-auto mb-6">
              Create your first learning space (e.g. &ldquo;Deep Learning&rdquo; or &ldquo;System Architecture&rdquo;) to begin.
            </p>
            <button
              onClick={() => setShowCreateSpace(true)}
              className="bg-primary-600 hover:bg-primary-500 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors inline-flex items-center gap-2"
            >
              <Plus className="w-4 h-4" /> Create First Space
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {spaces.map((space) => (
              <Link
                key={space.id}
                href={`/spaces/${space.id}`}
                className="group p-6 rounded-xl bg-surface border border-gray-800 hover:border-blue-700 transition-all shadow-md hover:shadow-xl hover:shadow-blue-900/10 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <span className="p-2.5 rounded-lg bg-blue-950/60 text-blue-400 border border-blue-900">
                      <Folder className="w-5 h-5" />
                    </span>
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      {space.visual_tag}
                    </span>
                  </div>
                  <h3 className="font-semibold text-lg text-white mb-1.5 group-hover:text-blue-400 transition-colors">
                    {space.name}
                  </h3>
                  <p className="text-xs text-gray-400 line-clamp-2 mb-6">
                    {space.description || "No description provided"}
                  </p>
                </div>
                <div className="pt-4 border-t border-gray-800 flex items-center justify-between text-xs text-gray-400 group-hover:text-white transition-colors">
                  <span>Explore Projects</span>
                  <ArrowRight className="w-4 h-4" />
                </div>
              </Link>
            ))}
          </div>
        )}

        {/* Projects Leaderboard & Global Activity Feed */}
        {globalAnalytics && globalAnalytics.projects_leaderboard.length > 0 && (
          <div className="mt-12 grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Leaderboard */}
            <div className="lg:col-span-2 p-6 rounded-2xl bg-surface border border-gray-800">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-cyan-400" /> Active Projects Leaderboard
                  </h3>
                  <p className="text-xs text-gray-400">Mastery and progress ranked across all spaces</p>
                </div>
              </div>

              <div className="space-y-3">
                {globalAnalytics.projects_leaderboard.map((item) => (
                  <Link
                    key={item.project_id}
                    href={`/projects/${item.project_id}/analytics`}
                    className="p-3.5 rounded-xl bg-surface-raised/60 hover:bg-surface-raised border border-gray-800/80 hover:border-gray-700 flex items-center justify-between transition-colors group"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-white group-hover:text-cyan-400 transition-colors text-sm">
                          {item.project_name}
                        </span>
                        <span className="text-[10px] bg-gray-800 text-gray-400 px-2 py-0.5 rounded border border-gray-700">
                          {item.space_name}
                        </span>
                      </div>
                      <div className="text-[11px] text-gray-400 mt-1 flex items-center gap-3">
                        <span>{item.materials_count} Materials</span>
                        <span>&bull;</span>
                        <span>{item.quizzes_count} Quizzes</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="text-sm font-bold text-white">{item.average_mastery}%</div>
                        <div className="text-[10px] text-gray-400">Avg Mastery</div>
                      </div>
                      <ArrowRight className="w-4 h-4 text-gray-500 group-hover:text-white transition-colors" />
                    </div>
                  </Link>
                ))}
              </div>
            </div>

            {/* Global Recent Activity Stream */}
            <div className="p-6 rounded-2xl bg-surface border border-gray-800 flex flex-col justify-between">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2 mb-1">
                  <Clock className="w-4 h-4 text-gray-400" /> Cross-Workspace Activity
                </h3>
                <p className="text-xs text-gray-400 mb-4">Latest learning events recorded</p>

                <div className="space-y-2.5">
                  {globalAnalytics.recent_events.length === 0 ? (
                    <p className="text-xs text-gray-500 py-3 text-center">No recent events logged</p>
                  ) : (
                    globalAnalytics.recent_events.slice(0, 5).map((evt) => (
                      <div key={evt.id} className="text-xs p-2.5 rounded-lg bg-surface-raised/50 border border-gray-800/60">
                        <div className="flex items-center justify-between text-[11px] text-gray-400 mb-0.5">
                          <span className="font-medium text-gray-300">{evt.event_type.replace(/_/g, " ")}</span>
                          <span>{new Date(evt.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                        <p className="text-[11px] text-gray-400 truncate">
                          {evt.payload.filename || evt.payload.concept_name || evt.payload.project_name || "Activity recorded"}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="pt-4 border-t border-gray-800 mt-4 text-center">
                <span className="text-[11px] text-gray-400">
                  Total AI telemetry logged: {globalAnalytics.overview.total_ai_interactions}
                </span>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Create Space Modal */}
      {showCreateSpace && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-surface border border-gray-800 rounded-2xl p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-1">Create New Learning Space</h3>
            <p className="text-xs text-gray-400 mb-6">Broad learning domain (e.g. Distributed Systems, AI Engineering)</p>

            <form onSubmit={handleCreateSpace} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">Space Name</label>
                <input
                  type="text"
                  required
                  value={spaceName}
                  onChange={(e) => setSpaceName(e.target.value)}
                  placeholder="Deep Learning Foundations"
                  className="w-full px-4 py-2 rounded-lg bg-surface-raised border border-gray-700 text-white text-sm focus:outline-none focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">Description</label>
                <textarea
                  rows={3}
                  value={spaceDesc}
                  onChange={(e) => setSpaceDesc(e.target.value)}
                  placeholder="Mastering core optimization and neural architectures."
                  className="w-full px-4 py-2 rounded-lg bg-surface-raised border border-gray-700 text-white text-sm focus:outline-none focus:border-primary-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setShowCreateSpace(false)}
                  className="px-4 py-2 text-sm text-gray-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm bg-primary-600 hover:bg-primary-500 text-white font-medium rounded-lg"
                >
                  Create Space
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
