"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Printer,
  Copy,
  Check,
  RotateCw,
  Sparkles,
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Clock,
  ExternalLink,
  HelpCircle,
  Award,
  Zap,
  Flame,
  Layers,
  ArrowRight
} from "lucide-react";
import { ApiClient } from "@/lib/api";
import { CheatSheetResponse } from "@/types";
import DocumentViewerModal from "@/components/DocumentViewerModal";

export default function CheatSheetPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  const [data, setData] = useState<CheatSheetResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [checkedItems, setCheckedItems] = useState<Record<string, boolean>>({});
  const [revealedQA, setRevealedQA] = useState<Record<number, boolean>>({});

  // Document Viewer Modal State
  const [activeViewer, setActiveViewer] = useState<{
    isOpen: boolean;
    materialId?: string;
    initialPage?: number;
    highlightSnippet?: string;
  } | null>(null);

  useEffect(() => {
    fetchCheatSheet();
  }, [projectId]);

  const fetchCheatSheet = async () => {
    try {
      setLoading(true);
      const res = await ApiClient.request<CheatSheetResponse>(`/projects/${projectId}/cheat-sheet`);
      setData(res);
    } catch (err) {
      console.error("Failed to load cheat sheet:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerate = async () => {
    try {
      setRegenerating(true);
      const res = await ApiClient.request<CheatSheetResponse>(
        `/projects/${projectId}/cheat-sheet/regenerate`,
        { method: "POST" }
      );
      setData(res);
    } catch (err) {
      console.error("Failed to regenerate cheat sheet:", err);
    } finally {
      setRegenerating(false);
    }
  };

  const toggleCheck = (id: string) => {
    setCheckedItems((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const toggleQA = (idx: number) => {
    setRevealedQA((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const handlePrint = () => {
    window.print();
  };

  const handleCopyMarkdown = () => {
    if (!data) return;

    let md = `# ${data.project_name} — High-Yield Exam Revision Cheat Sheet\n`;
    md += `*Generated: ${data.generated_at} | Readiness Score: ${data.exam_readiness_score}%*\n\n`;
    md += `**Learning Goal:** ${data.learning_goal}\n\n`;
    md += `---\n\n## ⚠️ Personalized Exam Traps & Misconceptions\n\n`;
    data.personalized_traps.forEach((t) => {
      md += `### ⚠️ ${t.misconception_title} (Source Page ${t.source_page || "N/A"})\n`;
      md += `* **What was missed:** ${t.what_student_missed}\n`;
      md += `* **Exam Trap Warning:** ${t.exam_trap_warning}\n`;
      md += `* **Correct Mental Model:** ${t.correct_mental_model}\n\n`;
    });

    md += `---\n\n## 📐 Core Formulas & Principles\n\n`;
    data.core_formulas.forEach((f) => {
      md += `### ${f.name}\n`;
      md += `\`\`\`\n${f.formula_or_rule}\n\`\`\`\n`;
      md += `* **Intuition:** ${f.plain_explanation}\n`;
      md += `* **Citation:** ${f.source_citation}\n\n`;
    });

    md += `---\n\n## ⚡ Rapid-Fire Q&A\n\n`;
    data.rapid_fire_qa.forEach((qa, idx) => {
      md += `**Q${idx + 1}: ${qa.question}**\n`;
      md += `> ${qa.quick_answer} *(Key Term: ${qa.key_term})*\n\n`;
    });

    navigator.clipboard.writeText(md);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4 text-center max-w-sm">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-amber-500"></div>
          <div>
            <h3 className="font-bold text-white text-base">Synthesizing Exam Revision Cheat Sheet...</h3>
            <p className="text-xs text-gray-400 mt-1">
              Analyzing study materials, formulas, and your diagnosed quiz mistakes to formulate high-yield revision notes.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-background p-6">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-12 h-12 text-amber-400 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-white">Could Not Generate Cheat Sheet</h2>
          <p className="text-xs text-gray-400 mt-1 mb-6">
            Ensure you have uploaded course materials to this project before generating an exam cheat sheet.
          </p>
          <Link
            href={`/projects/${projectId}`}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-xs font-semibold"
          >
            Back to Project
          </Link>
        </div>
      </div>
    );
  }

  const readinessColor =
    data.exam_readiness_score >= 80
      ? "text-emerald-400 border-emerald-800 bg-emerald-950/60"
      : data.exam_readiness_score >= 60
      ? "text-amber-400 border-amber-800 bg-amber-950/60"
      : "text-rose-400 border-rose-800 bg-rose-950/60";

  return (
    <div className="min-h-screen bg-background text-gray-100 flex flex-col print:bg-white print:text-black">
      {/* Top Navbar / Controls (Hidden in Print) */}
      <header className="border-b border-gray-800 bg-surface/80 backdrop-blur sticky top-0 z-30 px-6 py-3.5 flex items-center justify-between print:hidden">
        <div className="flex items-center gap-3">
          <Link
            href={`/projects/${projectId}`}
            className="p-2 rounded-lg bg-surface-raised border border-gray-700 text-gray-300 hover:text-white transition-colors"
            title="Back to Project"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1">
                <Zap className="w-3 h-3 fill-amber-400" /> High-Yield Revision
              </span>
              <span className="text-[10px] text-gray-500">&bull; {data.generated_at}</span>
            </div>
            <h1 className="text-sm sm:text-base font-bold text-white truncate max-w-md">
              {data.project_name} &mdash; Exam Cheat Sheet
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleCopyMarkdown}
            className="px-3 py-1.5 rounded-lg bg-surface-raised hover:bg-gray-800 border border-gray-700 text-gray-200 text-xs font-medium flex items-center gap-1.5 transition-colors shadow-sm"
            title="Copy entire cheat sheet as Markdown"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? "Copied!" : "Copy Markdown"}</span>
          </button>

          <button
            onClick={handlePrint}
            className="px-3 py-1.5 rounded-lg bg-surface-raised hover:bg-gray-800 border border-gray-700 text-gray-200 text-xs font-medium flex items-center gap-1.5 transition-colors shadow-sm"
            title="Print or Save as PDF"
          >
            <Printer className="w-3.5 h-3.5 text-blue-400" />
            <span>Print / PDF</span>
          </button>

          <button
            onClick={handleRegenerate}
            disabled={regenerating}
            className="px-3 py-1.5 rounded-lg bg-surface-raised hover:bg-gray-800 border border-gray-700 text-gray-200 text-xs font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50 shadow-sm"
            title="Regenerate with newest mistakes & materials"
          >
            <RotateCw className={`w-3.5 h-3.5 ${regenerating ? "animate-spin text-amber-400" : ""}`} />
            <span>{regenerating ? "Synthesizing..." : "Refresh"}</span>
          </button>

          <Link
            href={`/projects/${projectId}/quiz`}
            className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-amber-500/20 transition-all"
          >
            <span>Launch Quiz</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </header>

      {/* Main Content Viewport */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-4 sm:p-6 md:p-8 space-y-8 print:p-0 print:space-y-6">
        
        {/* Print Only Header */}
        <div className="hidden print:block border-b pb-4 mb-4">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-2xl font-black">{data.project_name} — Exam Revision Cheat Sheet</h1>
              <p className="text-xs text-gray-600 mt-1">Goal: {data.learning_goal}</p>
            </div>
            <div className="text-right text-xs">
              <span className="font-bold">Exam Readiness: {data.exam_readiness_score}%</span>
              <div className="text-gray-500">{data.generated_at}</div>
            </div>
          </div>
        </div>

        {/* Executive Overview Card (Web Only) */}
        <div className="p-6 rounded-2xl bg-gradient-to-r from-amber-950/30 via-surface to-surface border border-amber-800/50 shadow-xl print:hidden flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-900/60 border border-amber-700/60 text-amber-300 text-xs font-semibold uppercase tracking-wider mb-2.5">
              <Sparkles className="w-3.5 h-3.5" /> High-Yield Synthesis
            </div>
            <h2 className="text-xl sm:text-2xl font-black text-white">
              Personalized Exam Revision Guide
            </h2>
            <p className="text-xs sm:text-sm text-gray-300 mt-1.5 leading-relaxed">
              Synthesized from your uploaded study materials, formulas, and <span className="text-amber-300 font-semibold">{data.critical_traps_count} diagnosed conceptual mistakes</span> from previous quizzes.
            </p>
          </div>

          <div className="flex items-center gap-4 shrink-0 bg-surface-raised/80 border border-gray-800 p-4 rounded-xl shadow-inner">
            <div className="text-center">
              <div className={`text-2xl font-black px-3 py-1 rounded-lg border ${readinessColor}`}>
                {data.exam_readiness_score}%
              </div>
              <div className="text-[10px] uppercase font-bold text-gray-400 mt-1">Exam Readiness</div>
            </div>
            <div className="h-10 w-px bg-gray-700"></div>
            <div className="text-center">
              <div className="text-2xl font-black text-white">{data.total_concepts_covered}</div>
              <div className="text-[10px] uppercase font-bold text-gray-400 mt-1">Concepts Mapped</div>
            </div>
          </div>
        </div>

        {/* SECTION 1: PERSONALIZED EXAM TRAPS & MISCONCEPTIONS */}
        {data.personalized_traps.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400" />
                <span>⚠️ Personalized Exam Traps &amp; Common Misconceptions</span>
              </h3>
              <span className="text-xs text-rose-400 font-medium">
                Mined from your actual quiz errors
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.personalized_traps.map((trap, idx) => (
                <div
                  key={idx}
                  className="p-5 rounded-xl bg-gradient-to-br from-rose-950/30 to-surface border border-rose-900/50 shadow-md flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between text-xs mb-2">
                      <span className="font-bold text-rose-300 flex items-center gap-1.5">
                        <Flame className="w-3.5 h-3.5 text-rose-400" />
                        {trap.misconception_title}
                      </span>
                      {trap.source_page && (
                        <button
                          onClick={() =>
                            setActiveViewer({
                              isOpen: true,
                              initialPage: trap.source_page,
                              highlightSnippet: trap.correct_mental_model,
                            })
                          }
                          className="text-[11px] font-semibold text-amber-300 hover:text-amber-200 bg-amber-950/60 border border-amber-800/60 px-2 py-0.5 rounded flex items-center gap-1 transition-colors"
                          title="Open in Original PDF"
                        >
                          <BookOpen className="w-3 h-3" /> Page {trap.source_page} &rarr;
                        </button>
                      )}
                    </div>

                    <div className="text-xs space-y-2 text-gray-300">
                      <div className="p-2.5 rounded-lg bg-rose-950/40 border border-rose-900/40 text-rose-200">
                        <span className="font-bold text-rose-400">Previous Mistake:</span> &ldquo;{trap.what_student_missed}&rdquo;
                      </div>

                      <div className="text-xs leading-relaxed">
                        <span className="font-semibold text-amber-300">Exam Trap:</span> {trap.exam_trap_warning}
                      </div>

                      <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-900/40 text-emerald-200 font-medium leading-relaxed">
                        <span className="font-bold text-emerald-400">Correct Mental Model:</span> {trap.correct_mental_model}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* SECTION 2: CORE FORMULAS & MATHEMATICAL PRINCIPLES */}
        {data.core_formulas.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-cyan-400" />
                <span>📐 Core Formulas, Laws &amp; Algorithmic Rules</span>
              </h3>
              <span className="text-xs text-gray-400">Anchored with PDF page citations</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.core_formulas.map((formula, idx) => (
                <div
                  key={idx}
                  className="p-5 rounded-xl bg-surface border border-gray-800 hover:border-cyan-800/80 transition-all flex flex-col justify-between shadow-sm"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-bold text-white">{formula.name}</h4>
                      {formula.page_number && (
                        <button
                          onClick={() =>
                            setActiveViewer({
                              isOpen: true,
                              materialId: formula.material_id,
                              initialPage: formula.page_number,
                              highlightSnippet: formula.formula_or_rule,
                            })
                          }
                          className="text-[10px] font-semibold text-cyan-300 bg-cyan-950/80 border border-cyan-800 px-2 py-0.5 rounded hover:bg-cyan-900 transition-colors flex items-center gap-1"
                          title="Open Original PDF"
                        >
                          <BookOpen className="w-3 h-3" /> Page {formula.page_number}
                        </button>
                      )}
                    </div>

                    <div className="my-2.5 p-3 rounded-lg bg-black/70 border border-gray-800 font-mono text-xs sm:text-sm text-cyan-300 font-bold overflow-x-auto">
                      {formula.formula_or_rule}
                    </div>

                    <p className="text-xs text-gray-300 leading-relaxed">
                      {formula.plain_explanation}
                    </p>
                  </div>

                  <div className="mt-4 pt-2.5 border-t border-gray-800/80 text-[11px] text-gray-500 truncate">
                    {formula.source_citation}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* SECTION 3: HIGH-YIELD CONCEPT SUMMARY CHECKLIST */}
        {data.high_yield_concepts.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>📊 High-Yield Concept Revision Checklist</span>
              </h3>
              <span className="text-xs text-gray-400">Click checkboxes to mark off revision items</span>
            </div>

            <div className="bg-surface border border-gray-800 rounded-xl overflow-hidden divide-y divide-gray-800">
              {data.high_yield_concepts.map((concept, idx) => {
                const isChecked = checkedItems[concept.concept_name] || false;
                const masteryPill =
                  concept.mastery_score >= 75
                    ? "bg-emerald-950/80 border-emerald-800 text-emerald-300"
                    : concept.mastery_score >= 50
                    ? "bg-amber-950/80 border-amber-800 text-amber-300"
                    : "bg-rose-950/80 border-rose-800 text-rose-300";

                return (
                  <div
                    key={idx}
                    onClick={() => toggleCheck(concept.concept_name)}
                    className={`p-4 flex items-start justify-between gap-4 cursor-pointer transition-colors ${
                      isChecked ? "bg-surface-raised/40 opacity-60" : "hover:bg-surface-raised/50"
                    }`}
                  >
                    <div className="flex items-start gap-3 min-w-0">
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => {}}
                        className="mt-1 rounded border-gray-700 text-amber-500 focus:ring-0 cursor-pointer"
                      />
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span
                            className={`text-sm font-bold ${
                              isChecked ? "line-through text-gray-400" : "text-white"
                            }`}
                          >
                            {concept.concept_name}
                          </span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${masteryPill}`}>
                            Mastery: {concept.mastery_score}%
                          </span>
                        </div>
                        <p className="text-xs text-gray-300 mt-1 leading-relaxed">
                          {concept.key_takeaway}
                        </p>
                      </div>
                    </div>

                    {concept.page_number && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveViewer({
                            isOpen: true,
                            initialPage: concept.page_number,
                            highlightSnippet: concept.key_takeaway,
                          });
                        }}
                        className="text-[11px] shrink-0 text-blue-400 hover:text-blue-300 flex items-center gap-1 font-medium mt-1"
                        title="View page in PDF"
                      >
                        <BookOpen className="w-3 h-3" /> Page {concept.page_number}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* SECTION 4: RAPID-FIRE ACTIVE RECALL Q&A */}
        {data.rapid_fire_qa.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-400" />
                <span>⚡ 5-Minute Rapid-Fire Active Recall Q&amp;A</span>
              </h3>
              <span className="text-xs text-gray-400">Click question to reveal the exam answer</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {data.rapid_fire_qa.map((qa, idx) => {
                const isRevealed = revealedQA[idx] || false;
                return (
                  <div
                    key={idx}
                    onClick={() => toggleQA(idx)}
                    className="p-4 rounded-xl bg-surface border border-gray-800 hover:border-gray-700 cursor-pointer transition-all flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between text-xs font-semibold text-gray-400 mb-1.5">
                        <span className="text-amber-400 uppercase tracking-wider text-[10px]">
                          Key Term: {qa.key_term}
                        </span>
                        <span className="text-[10px] text-gray-500">
                          {isRevealed ? "Click to hide" : "Click to reveal"}
                        </span>
                      </div>
                      <p className="text-xs sm:text-sm font-bold text-white mb-2">{qa.question}</p>
                      {isRevealed ? (
                        <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/60 text-xs text-amber-100 font-medium leading-relaxed animate-fadeIn">
                          {qa.quick_answer}
                        </div>
                      ) : (
                        <div className="p-2.5 rounded-lg bg-surface-raised border border-dashed border-gray-700 text-[11px] text-gray-500 italic text-center">
                          Tap to check your answer before looking...
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* SECTION 5: 15-MINUTE PRE-EXAM CRAMMING CHECKLIST */}
        {data.cramming_checklist.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Clock className="w-4 h-4 text-purple-400" />
                <span>🕒 15-Minute Pre-Exam Action Plan</span>
              </h3>
              <span className="text-xs text-purple-300">Final sanity checkpoints</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {data.cramming_checklist.map((item) => {
                const isDone = checkedItems[item.id] || false;
                return (
                  <div
                    key={item.id}
                    onClick={() => toggleCheck(item.id)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all flex items-start gap-3 ${
                      isDone
                        ? "bg-surface-raised/30 border-gray-800/50 opacity-50"
                        : item.is_critical
                        ? "bg-rose-950/20 border-rose-900/50 hover:border-rose-700"
                        : "bg-surface border-gray-800 hover:border-gray-700"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isDone}
                      onChange={() => {}}
                      className="mt-0.5 rounded border-gray-700 text-purple-500 focus:ring-0 cursor-pointer"
                    />
                    <div className="min-w-0 flex-1 text-xs">
                      <div className="flex items-center justify-between gap-1 mb-1">
                        <span className={`font-semibold ${isDone ? "line-through text-gray-400" : "text-white"}`}>
                          {item.task}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-gray-400">
                        <span>~{item.estimated_mins} mins</span>
                        {item.is_critical && (
                          <span className="text-rose-400 font-bold uppercase tracking-wider">
                            Critical Weakness
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* BOTTOM CTA: LAUNCH CRAMMING QUIZ */}
        <div className="p-8 rounded-2xl bg-gradient-to-r from-amber-950/60 via-surface to-surface border border-amber-800/80 shadow-xl print:hidden flex flex-col sm:flex-row items-center justify-between gap-6">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Award className="w-5 h-5 text-amber-400" />
              <span>Ready to test your retention under exam conditions?</span>
            </h3>
            <p className="text-xs text-gray-300 mt-1 max-w-xl">
              Launch a targeted adaptive quiz specifically focused on the formulas and potential traps covered on this cheat sheet.
            </p>
          </div>
          <Link
            href={`/projects/${projectId}/quiz`}
            className="px-6 py-3 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-bold text-sm shadow-lg shadow-amber-600/30 transition-all flex items-center gap-2 shrink-0 hover:scale-105"
          >
            <span>Start Practice Exam Quiz</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

      </main>

      {/* In-Browser Document Viewer Modal for Page Citations */}
      {activeViewer?.isOpen && (
        <DocumentViewerModal
          projectId={projectId}
          materialId={activeViewer.materialId}
          initialPage={activeViewer.initialPage}
          highlightSnippet={activeViewer.highlightSnippet}
          onClose={() => setActiveViewer(null)}
        />
      )}
    </div>
  );
}
