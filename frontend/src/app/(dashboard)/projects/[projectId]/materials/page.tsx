"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Upload, FileText, CheckCircle2, AlertCircle, Clock, Trash2, Brain, ArrowRight, RefreshCw, BookOpen } from "lucide-react";
import { ApiClient } from "@/lib/api";
import { Material, Concept } from "@/types";
import DocumentViewerModal from "@/components/DocumentViewerModal";

export default function MaterialsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  const [materials, setMaterials] = useState<Material[]>([]);
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [activeViewer, setActiveViewer] = useState<{ isOpen: boolean; materialId?: string; documentTitle?: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchMaterialsAndConcepts();
  }, [projectId]);

  // Polling loop: If any document is QUEUED or PROCESSING, refresh every 3 seconds
  useEffect(() => {
    const hasActiveJobs = materials.some(
      (m) => m.status === "QUEUED" || m.status === "PROCESSING"
    );

    if (hasActiveJobs) {
      const interval = setInterval(() => {
        fetchMaterialsAndConcepts();
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [materials]);

  const fetchMaterialsAndConcepts = async () => {
    try {
      const mats = await ApiClient.request<Material[]>(`/projects/${projectId}/materials`);
      setMaterials(mats);
      const concs = await ApiClient.request<Concept[]>(`/projects/${projectId}/concepts`);
      setConcepts(concs);
    } catch (err) {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("Please upload a PDF document.");
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      await ApiClient.uploadFile(`/projects/${projectId}/materials`, formData);
      fetchMaterialsAndConcepts();
    } catch (err: any) {
      alert(err.message || "Failed to upload file");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleRetry = async (materialId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await ApiClient.request(`/projects/${projectId}/materials/${materialId}/retry`, {
        method: "POST",
      });
      fetchMaterialsAndConcepts();
    } catch (err: any) {
      alert(err.message || "Failed to restart processing");
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Top Header */}
      <header className="border-b border-gray-800 bg-surface/50 backdrop-blur px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href={`/projects/${projectId}`}
            className="text-gray-400 hover:text-white p-2 rounded-lg hover:bg-surface transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider">Project Materials</span>
            <h1 className="text-xl font-bold text-white">Learning Materials &amp; Ingestion</h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchMaterialsAndConcepts()}
            className="text-xs text-gray-400 hover:text-white p-2 rounded-lg hover:bg-surface transition-colors flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh Status
          </button>
          <Link
            href={`/projects/${projectId}/tutor`}
            className="bg-primary-600 hover:bg-primary-500 text-white text-xs font-medium px-4 py-2 rounded-lg transition-colors flex items-center gap-1.5 shadow-lg shadow-blue-500/20"
          >
            Go to AI Tutor <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8 space-y-8">
        {/* Drag and Drop Upload Box */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`p-10 border-2 border-dashed rounded-2xl flex flex-col items-center justify-center text-center cursor-pointer transition-all ${
            dragActive
              ? "border-primary-500 bg-primary-950/20"
              : "border-gray-800 bg-surface hover:border-gray-700"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
          />
          <div className="p-4 rounded-full bg-blue-950/60 text-blue-400 border border-blue-900 mb-4">
            <Upload className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-white mb-1">
            {uploading ? "Uploading & Enqueuing Ingestion..." : "Upload Study Material (PDF)"}
          </h3>
          <p className="text-xs text-gray-400 max-w-sm mb-4">
            Drag and drop your notes, slides, or textbook chapter. Processing, OCR, chunking, and concept extraction occur asynchronously.
          </p>
          <span className="text-xs text-blue-400 font-medium">Browse Files on Computer</span>
        </div>

        {/* Uploaded Materials Table */}
        <div className="bg-surface border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-400" /> Uploaded Documents ({materials.length})
            </h2>
            <span className="text-xs text-gray-500">PDF is primary format</span>
          </div>

          {materials.length === 0 ? (
            <div className="p-8 text-center text-xs text-gray-500">
              No documents uploaded yet. Upload a PDF above to ground the AI Tutor.
            </div>
          ) : (
            <div className="divide-y divide-gray-800">
              {materials.map((m) => (
                <div key={m.id} className="px-6 py-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-gray-400" />
                    <div>
                      <p className="text-sm font-medium text-white">{m.filename}</p>
                      <p className="text-xs text-gray-500">
                        {(m.file_size_bytes / (1024 * 1024)).toFixed(2)} MB • {m.total_pages} Pages
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    {/* Status Badge */}
                    {m.status === "QUEUED" && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-950/60 text-amber-400 border border-amber-800">
                        <Clock className="w-3.5 h-3.5 animate-pulse" /> Queued
                      </span>
                    )}
                    {m.status === "PROCESSING" && (
                      <div className="flex items-center gap-2">
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-blue-950/60 text-blue-400 border border-blue-800">
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Processing &amp; OCR
                        </span>
                        <button
                          onClick={(e) => handleRetry(m.id, e)}
                          title="Restart processing if stuck"
                          className="text-xs px-2.5 py-1 rounded bg-surface hover:bg-surface-raised border border-gray-700 text-gray-300 hover:text-white transition-colors"
                        >
                          Retry
                        </button>
                      </div>
                    )}
                    {m.status === "READY" && (
                      <div className="flex items-center gap-2">
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-800">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Ready for Learning
                        </span>
                        <button
                          onClick={() => setActiveViewer({ isOpen: true, materialId: m.id, documentTitle: m.filename })}
                          className="text-xs px-3 py-1 rounded-lg bg-blue-950/80 hover:bg-blue-900 border border-blue-800 text-blue-300 font-medium transition-colors flex items-center gap-1.5 shadow-sm"
                        >
                          <BookOpen className="w-3.5 h-3.5" /> View Original PDF
                        </button>
                      </div>
                    )}
                    {m.status === "FAILED" && (
                      <div className="flex items-center gap-2">
                        <span
                          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-rose-950/60 text-rose-400 border border-rose-800"
                          title={m.error_message || "Error occurred"}
                        >
                          <AlertCircle className="w-3.5 h-3.5" /> Failed
                        </span>
                        <button
                          onClick={(e) => handleRetry(m.id, e)}
                          className="text-xs px-2.5 py-1 rounded bg-surface hover:bg-surface-raised border border-gray-700 text-gray-300 hover:text-white transition-colors"
                        >
                          Retry
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Extracted Concepts & Knowledge Preview */}
        {concepts.length > 0 && (
          <div className="bg-surface border border-gray-800 rounded-xl p-6">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
              <Brain className="w-4 h-4 text-indigo-400" /> Extracted Atomic Concepts ({concepts.length})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {concepts.map((c) => (
                <div key={c.id} className="p-4 rounded-lg bg-surface-raised border border-gray-700/50">
                  <div className="flex items-center justify-between mb-1.5">
                    <h3 className="font-semibold text-sm text-white">{c.name}</h3>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-900">
                      Score: {c.importance_score}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 leading-relaxed">{c.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Document Viewer Modal */}
        {activeViewer?.isOpen && (
          <DocumentViewerModal
            projectId={projectId}
            materialId={activeViewer.materialId}
            documentTitle={activeViewer.documentTitle}
            onClose={() => setActiveViewer(null)}
          />
        )}
      </main>
    </div>
  );
}
