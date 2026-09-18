"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Brain, Plus, Target, ArrowRight, BookOpen, Layers } from "lucide-react";
import { ApiClient } from "@/lib/api";
import { Space, Project } from "@/types";

export default function SpaceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const spaceId = params.spaceId as string;

  const [space, setSpace] = useState<Space | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [projName, setProjName] = useState("");
  const [projDesc, setProjDesc] = useState("");
  const [projGoal, setProjGoal] = useState("");

  useEffect(() => {
    fetchSpaceAndProjects();
  }, [spaceId]);

  const fetchSpaceAndProjects = async () => {
    try {
      const spaceData = await ApiClient.request<Space>(`/spaces/${spaceId}`);
      setSpace(spaceData);
      const projData = await ApiClient.request<Project[]>(`/spaces/${spaceId}/projects`);
      setProjects(projData);
    } catch (err) {
      router.push("/dashboard");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await ApiClient.request(`/spaces/${spaceId}/projects`, {
        method: "POST",
        body: JSON.stringify({
          name: projName,
          description: projDesc,
          learning_goal: projGoal,
        }),
      });
      setProjName("");
      setProjDesc("");
      setProjGoal("");
      setShowCreateModal(false);
      fetchSpaceAndProjects();
    } catch (err: any) {
      alert(err.message || "Failed to create project");
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
    <div className="min-h-screen bg-background">
      {/* Top bar */}
      <header className="border-b border-gray-800 bg-surface/50 backdrop-blur px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/dashboard"
            className="text-gray-400 hover:text-white p-2 rounded-lg hover:bg-surface transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider">Learning Space</span>
            <h1 className="text-xl font-bold text-white">{space?.name}</h1>
          </div>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-primary-600 hover:bg-primary-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors flex items-center gap-2 shadow-lg shadow-blue-500/20"
        >
          <Plus className="w-4 h-4" /> New Project
        </button>
      </header>

      {/* Main Container */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {space?.description && (
          <p className="text-sm text-gray-400 max-w-3xl mb-8 leading-relaxed">
            {space.description}
          </p>
        )}

        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-blue-400" /> Focused Learning Projects
          </h2>
          <span className="text-xs text-gray-400">{projects.length} Projects in this Space</span>
        </div>

        {projects.length === 0 ? (
          <div className="p-12 text-center rounded-2xl bg-surface border border-gray-800">
            <Target className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-white mb-2">No projects created yet</h3>
            <p className="text-sm text-gray-400 max-w-md mx-auto mb-6">
              A Project represents a focused learning journey with an explicit goal. Create one to begin uploading materials.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="bg-primary-600 hover:bg-primary-500 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors inline-flex items-center gap-2"
            >
              <Plus className="w-4 h-4" /> Create Focused Project
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {projects.map((project) => (
              <Link
                key={project.id}
                href={`/projects/${project.id}`}
                className="group p-6 rounded-xl bg-surface border border-gray-800 hover:border-blue-700 transition-all shadow-md hover:shadow-xl flex flex-col justify-between"
              >
                <div>
                  <h3 className="font-semibold text-lg text-white mb-2 group-hover:text-blue-400 transition-colors">
                    {project.name}
                  </h3>
                  {project.description && (
                    <p className="text-xs text-gray-400 mb-4 line-clamp-2">
                      {project.description}
                    </p>
                  )}
                  <div className="p-3 rounded-lg bg-surface-raised border border-gray-700/50 mb-6">
                    <span className="text-[10px] font-bold text-blue-400 uppercase tracking-wider block mb-1">
                      Target Learning Goal
                    </span>
                    <p className="text-xs text-gray-300 line-clamp-2">
                      {project.learning_goal}
                    </p>
                  </div>
                </div>

                <div className="pt-4 border-t border-gray-800 flex items-center justify-between text-xs text-gray-400 group-hover:text-white transition-colors">
                  <span>Open Project Workspace</span>
                  <ArrowRight className="w-4 h-4" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-surface border border-gray-800 rounded-2xl p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-1">Create Focused Project</h3>
            <p className="text-xs text-gray-400 mb-6">Define a specific journey and verifiable learning goal.</p>

            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">Project Name</label>
                <input
                  type="text"
                  required
                  value={projName}
                  onChange={(e) => setProjName(e.target.value)}
                  placeholder="Backpropagation & Neural Optimization"
                  className="w-full px-4 py-2 rounded-lg bg-surface-raised border border-gray-700 text-white text-sm focus:outline-none focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">Target Learning Goal (Required)</label>
                <textarea
                  rows={2}
                  required
                  value={projGoal}
                  onChange={(e) => setProjGoal(e.target.value)}
                  placeholder="Understand multi-layer perceptron gradients, avoid vanishing gradients, and compare convergence."
                  className="w-full px-4 py-2 rounded-lg bg-surface-raised border border-gray-700 text-white text-sm focus:outline-none focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-gray-400 mb-1">Description (Optional)</label>
                <textarea
                  rows={2}
                  value={projDesc}
                  onChange={(e) => setProjDesc(e.target.value)}
                  placeholder="Notes from CS231n and Deep Learning textbook."
                  className="w-full px-4 py-2 rounded-lg bg-surface-raised border border-gray-700 text-white text-sm focus:outline-none focus:border-primary-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-sm text-gray-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm bg-primary-600 hover:bg-primary-500 text-white font-medium rounded-lg"
                >
                  Create Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
