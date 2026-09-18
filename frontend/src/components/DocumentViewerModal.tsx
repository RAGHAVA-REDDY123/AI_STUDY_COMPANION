"use client";

import { useEffect, useState } from "react";
import {
  X,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  FileText,
  ExternalLink,
  Sparkles,
  Layers,
  FileCheck,
  RotateCcw
} from "lucide-react";
import { ApiClient } from "@/lib/api";

interface PageChunk {
  chunk_id: string;
  section_title: string;
  content: string;
  token_count: number;
}

interface DocumentPage {
  page_number: number;
  chunks: PageChunk[];
}

interface DocumentReaderData {
  material_id: string;
  filename: string;
  total_pages: number;
  pages: DocumentPage[];
}

interface MaterialSummary {
  id: string;
  filename: string;
  total_pages?: number;
}

interface DocumentViewerModalProps {
  projectId: string;
  materialId?: string;
  documentTitle?: string;
  initialPage?: number;
  highlightSnippet?: string;
  onClose: () => void;
}

export default function DocumentViewerModal({
  projectId,
  materialId,
  documentTitle,
  initialPage = 1,
  highlightSnippet,
  onClose,
}: DocumentViewerModalProps) {
  const [materials, setMaterials] = useState<MaterialSummary[]>([]);
  const [selectedMaterialId, setSelectedMaterialId] = useState<string | undefined>(materialId);
  const [data, setData] = useState<DocumentReaderData | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState<number>(initialPage);
  const [viewMode, setViewMode] = useState<"pdf" | "reader">("pdf");

  // 1. Fetch materials list and resolve effective material ID
  useEffect(() => {
    let isMounted = true;
    const loadMaterials = async () => {
      try {
        const list = await ApiClient.request<MaterialSummary[]>(`/projects/${projectId}/materials`);
        if (!isMounted) return;
        setMaterials(list);

        // If no materialId was passed or to ensure match:
        if (!selectedMaterialId) {
          if (documentTitle) {
            const match = list.find(
              (m) =>
                m.filename.toLowerCase().includes(documentTitle.toLowerCase()) ||
                documentTitle.toLowerCase().includes(m.filename.toLowerCase())
            );
            if (match) {
              setSelectedMaterialId(match.id);
              return;
            }
          }
          if (list.length > 0) {
            setSelectedMaterialId(list[0].id);
          }
        }
      } catch (err) {
        console.error("Failed to fetch project materials:", err);
      }
    };

    loadMaterials();
    return () => {
      isMounted = false;
    };
  }, [projectId, materialId, documentTitle]);

  // Synchronize when initialPage prop changes
  useEffect(() => {
    if (initialPage) {
      setCurrentPage(initialPage);
    }
  }, [initialPage]);

  // Synchronize materialId prop
  useEffect(() => {
    if (materialId) {
      setSelectedMaterialId(materialId);
    }
  }, [materialId]);

  // Load reader chunk data lazily if needed or for page count
  useEffect(() => {
    if (!selectedMaterialId) return;

    let isMounted = true;
    const fetchReaderData = async () => {
      try {
        setLoading(true);
        const res = await ApiClient.request<DocumentReaderData>(
          `/projects/${projectId}/materials/${selectedMaterialId}/reader`
        );
        if (!isMounted) return;
        setData(res);
      } catch (err) {
        console.warn("Failed to load document reader chunks:", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchReaderData();
    return () => {
      isMounted = false;
    };
  }, [selectedMaterialId, projectId]);

  // Calculate clean base URL & authenticated raw PDF stream URL
  const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  const baseUrl = rawApiUrl.replace(/\/+api\/+v1\/?$/, "");
  const token = typeof window !== "undefined" ? localStorage.getItem("study_companion_token") || "" : "";

  const activeMaterial = materials.find((m) => m.id === selectedMaterialId);
  const currentDocName = activeMaterial?.filename || data?.filename || documentTitle || "Original PDF Document";

  const totalPages =
    activeMaterial?.total_pages && activeMaterial.total_pages > 0
      ? activeMaterial.total_pages
      : data?.total_pages && data.total_pages > 0
      ? data.total_pages
      : data?.pages?.length || 1;

  const rawPdfUrl = selectedMaterialId
    ? `${baseUrl}/api/v1/projects/${projectId}/materials/${selectedMaterialId}/raw${
        token ? `?token=${encodeURIComponent(token)}` : ""
      }`
    : "";

  const pageData = data?.pages.find((p) => p.page_number === currentPage);

  const handlePrev = () => {
    if (currentPage > 1) setCurrentPage((p) => p - 1);
  };

  const handleNext = () => {
    if (currentPage < totalPages) setCurrentPage((p) => p + 1);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-2 sm:p-4 md:p-6 animate-fadeIn">
      <div className="w-full max-w-6xl h-[92vh] bg-surface border border-gray-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        
        {/* Top Header */}
        <div className="border-b border-gray-800 px-5 py-3.5 flex items-center justify-between bg-surface-raised/90 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2 rounded-xl bg-blue-950 border border-blue-800 text-blue-400 shrink-0">
              <BookOpen className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[11px] font-bold uppercase tracking-wider text-blue-400 flex items-center gap-1">
                  <FileCheck className="w-3 h-3" /> Original Source PDF
                </span>
                {initialPage && (
                  <span className="text-[10px] bg-amber-950/80 border border-amber-800 text-amber-300 px-2 py-0.5 rounded-full font-semibold">
                    Anchored to Page {initialPage}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm sm:text-base font-bold text-white truncate max-w-sm sm:max-w-md">
                  {currentDocName}
                </h2>
                {materials.length > 1 && (
                  <select
                    value={selectedMaterialId}
                    onChange={(e) => {
                      setSelectedMaterialId(e.target.value);
                      setCurrentPage(1);
                    }}
                    className="text-xs bg-gray-900 border border-gray-700 text-gray-300 rounded px-2 py-0.5 focus:outline-none focus:border-blue-500"
                  >
                    {materials.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.filename}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            {/* View Mode Toggle: Default to Original PDF */}
            <div className="flex items-center bg-gray-900 p-1 rounded-xl border border-gray-800 text-xs">
              <button
                onClick={() => setViewMode("pdf")}
                className={`px-3 py-1 rounded-lg font-semibold transition-all flex items-center gap-1.5 ${
                  viewMode === "pdf"
                    ? "bg-primary-600 text-white shadow-md"
                    : "text-gray-400 hover:text-white"
                }`}
                title="View authentic original PDF document"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Original PDF</span>
              </button>
              <button
                onClick={() => setViewMode("reader")}
                className={`px-3 py-1 rounded-lg font-semibold transition-all flex items-center gap-1.5 ${
                  viewMode === "reader"
                    ? "bg-primary-600 text-white shadow-md"
                    : "text-gray-400 hover:text-white"
                }`}
                title="Inspect extracted OCR text chunks"
              >
                <Layers className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Text Chunks</span>
              </button>
            </div>

            {rawPdfUrl && (
              <a
                href={`${rawPdfUrl}#page=${currentPage}`}
                target="_blank"
                rel="noreferrer"
                className="hidden sm:inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-surface-raised border border-gray-700 text-gray-300 hover:text-white text-xs font-medium transition-colors"
                title="Open PDF in a new browser window"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>New Tab</span>
              </a>
            )}

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
              title="Close Viewer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Grounded Evidence Proof Callout Banner */}
        {highlightSnippet && (
          <div className="bg-gradient-to-r from-amber-950/60 via-amber-950/40 to-surface-raised border-b border-amber-800/60 px-5 py-2.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5 shrink-0">
            <div className="flex items-start gap-2 min-w-0">
              <Sparkles className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400">
                    Grounded Citation Proof
                  </span>
                  <span className="text-[10px] bg-amber-900/80 border border-amber-700/60 text-amber-200 px-2 py-0.2 rounded-full font-medium">
                    Cited on Page {initialPage}
                  </span>
                </div>
                <p className="text-xs text-amber-100 font-medium italic mt-0.5 line-clamp-2">
                  &ldquo;{highlightSnippet}&rdquo;
                </p>
              </div>
            </div>

            {currentPage !== initialPage && (
              <button
                onClick={() => setCurrentPage(initialPage)}
                className="shrink-0 text-xs font-semibold px-3 py-1 rounded-md bg-amber-600 hover:bg-amber-500 text-white transition-colors flex items-center gap-1"
              >
                <RotateCcw className="w-3 h-3" /> Jump to Proof (Page {initialPage})
              </button>
            )}
          </div>
        )}

        {/* Page Navigation Toolbar */}
        <div className="border-b border-gray-800/80 px-5 py-2 bg-surface/80 flex items-center justify-between text-xs shrink-0">
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrev}
              disabled={currentPage <= 1}
              className="p-1 rounded bg-surface-raised border border-gray-700 text-gray-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              title="Previous Page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-semibold text-white px-2">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={handleNext}
              disabled={currentPage >= totalPages}
              className="p-1 rounded bg-surface-raised border border-gray-700 text-gray-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              title="Next Page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <div className="text-xs text-gray-400 flex items-center gap-2">
            <span>Viewing in browser</span>
            {rawPdfUrl && (
              <span className="hidden md:inline text-[11px] text-gray-500">
                &bull; Built-in PDF Engine
              </span>
            )}
          </div>
        </div>

        {/* Modal Main Viewport */}
        <div className="flex-1 w-full h-full overflow-hidden bg-neutral-950 relative flex flex-col">
          {viewMode === "pdf" ? (
            rawPdfUrl ? (
              <div className="w-full h-full flex flex-col bg-neutral-900">
                <iframe
                  key={`${selectedMaterialId}-p${currentPage}`}
                  src={`${rawPdfUrl}#page=${currentPage}&view=FitH`}
                  className="w-full h-full border-0 bg-neutral-900"
                  title={currentDocName}
                />
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center gap-3 p-6 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
                <p className="text-xs text-gray-400">Loading original PDF stream...</p>
              </div>
            )
          ) : (
            /* Structured Chunks Inspection View */
            <div className="flex-1 overflow-y-auto p-6 bg-background/50">
              <div className="max-w-3xl mx-auto space-y-6">
                <div className="p-3.5 rounded-xl bg-blue-950/40 border border-blue-800/60 text-xs text-blue-200">
                  <span className="font-semibold">Text Extraction Inspection:</span> Below are the raw text chunks
                  indexed for Page {currentPage}. The AI Tutor grounds its citations against these chunks, and anchors directly to the original PDF above.
                </div>

                {loading ? (
                  <div className="py-12 flex flex-col items-center justify-center gap-3">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
                    <p className="text-xs text-gray-400">Loading extracted text chunks...</p>
                  </div>
                ) : pageData && pageData.chunks.length > 0 ? (
                  pageData.chunks.map((chunk, idx) => {
                    const isSnippetMatch =
                      highlightSnippet &&
                      chunk.content.toLowerCase().includes(highlightSnippet.slice(0, 40).toLowerCase());

                    return (
                      <div
                        key={chunk.chunk_id}
                        className={`p-5 rounded-xl border transition-colors ${
                          isSnippetMatch
                            ? "bg-amber-950/30 border-amber-700/80 shadow-lg shadow-amber-900/10"
                            : "bg-surface border-gray-800"
                        }`}
                      >
                        <div className="flex items-center justify-between text-[11px] text-gray-400 mb-2 border-b border-gray-800 pb-2">
                          <span className="font-semibold text-blue-400 uppercase tracking-wider">
                            Section: {chunk.section_title}
                          </span>
                          <span>Chunk #{idx + 1} &bull; {chunk.token_count} tokens</span>
                        </div>
                        <p className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">
                          {chunk.content}
                        </p>
                      </div>
                    );
                  })
                ) : (
                  <div className="p-12 text-center rounded-xl bg-surface border border-gray-800 text-gray-400">
                    <p className="text-sm">No text chunks extracted on Page {currentPage}.</p>
                    <p className="text-xs text-gray-500 mt-1">This page may contain scanned diagrams or blank spacing.</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
