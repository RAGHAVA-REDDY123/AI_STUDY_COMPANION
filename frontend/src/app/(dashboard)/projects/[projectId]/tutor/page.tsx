"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Send, Sparkles, Brain, BookOpen, AlertCircle, Eye, Info, User as UserIcon, Award, Activity } from "lucide-react";
import { ApiClient } from "@/lib/api";
import { Message, Citation, ToolInvocation } from "@/types";
import DocumentViewerModal from "@/components/DocumentViewerModal";

export default function TutorChatPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  const [messages, setMessages] = useState<Message[]>([
    {
      role: "ASSISTANT",
      content: "Hello! I am your AI Study Tutor. I answer strictly based on your uploaded project notes and provide exact page citations. What concept would you like to explore today?",
      citations: [],
    },
  ]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [inspectDrawerOpen, setInspectDrawerOpen] = useState(false);
  const [activeCitations, setActiveCitations] = useState<Citation[]>([]);
  const [projectMaterials, setProjectMaterials] = useState<{ id: string; filename: string }[]>([]);
  const [activeViewer, setActiveViewer] = useState<{
    isOpen: boolean;
    materialId?: string;
    documentTitle?: string;
    initialPage?: number;
    highlightSnippet?: string;
  } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ApiClient.request<{ id: string; filename: string }[]>(`/projects/${projectId}/materials`)
      .then(setProjectMaterials)
      .catch(() => {});
  }, [projectId]);

  const openCitationInViewer = (c: Citation) => {
    let targetMatId = c.material_id;
    if (!targetMatId && projectMaterials.length > 0) {
      const match = projectMaterials.find(
        (m) =>
          m.filename.toLowerCase().includes(c.document_title.toLowerCase()) ||
          c.document_title.toLowerCase().includes(m.filename.toLowerCase())
      );
      targetMatId = match ? match.id : projectMaterials[0].id;
    }
    setActiveViewer({
      isOpen: true,
      materialId: targetMatId,
      documentTitle: c.document_title,
      initialPage: c.page_number,
      highlightSnippet: c.snippet,
    });
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (queryText?: string) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || isStreaming) return;

    setInput("");
    const userMessage: Message = { role: "USER", content: textToSend };
    setMessages((prev) => [...prev, userMessage]);
    setIsStreaming(true);

    try {
      const token = localStorage.getItem("study_companion_token");
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/projects/${projectId}/tutor/chat`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            content: textToSend,
            conversation_id: conversationId,
          }),
        }
      );

      if (!res.ok) {
        throw new Error("Failed to connect to Tutor service");
      }

      const reader = res.body?.getReader();
      if (!reader) return;

      const decoder = new TextDecoder();
      let assistantMsg: Message = {
        role: "ASSISTANT",
        content: "",
        citations: [],
        is_unsupported_refusal: false,
      };

      setMessages((prev) => [...prev, assistantMsg]);

      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event: init")) {
            const dataStr = line.replace("event: init\ndata: ", "");
            const parsed = JSON.parse(dataStr);
            setConversationId(parsed.conversation_id);
          } else if (line.startsWith("event: citations")) {
            const dataStr = line.replace("event: citations\ndata: ", "");
            const parsed = JSON.parse(dataStr);
            assistantMsg.citations = parsed.citations || [];
            setActiveCitations(parsed.citations || []);
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = { ...assistantMsg };
              return updated;
            });
          } else if (line.startsWith("event: tool_call")) {
            const dataStr = line.replace("event: tool_call\ndata: ", "");
            const parsed = JSON.parse(dataStr);
            const currentTools = assistantMsg.tools_invoked || [];
            currentTools.push({ tool: parsed.tool, arguments: parsed.arguments });
            assistantMsg.tools_invoked = [...currentTools];
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = { ...assistantMsg };
              return updated;
            });
          } else if (line.startsWith("event: tool_result")) {
            const dataStr = line.replace("event: tool_result\ndata: ", "");
            const parsed = JSON.parse(dataStr);
            if (assistantMsg.tools_invoked && assistantMsg.tools_invoked.length > 0) {
              const lastTool = assistantMsg.tools_invoked[assistantMsg.tools_invoked.length - 1];
              lastTool.result = parsed.result;
            }
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = { ...assistantMsg };
              return updated;
            });
          } else if (line.startsWith("event: chunk")) {
            const dataStr = line.replace("event: chunk\ndata: ", "");
            const parsed = JSON.parse(dataStr);
            assistantMsg.content += parsed.text;

            if (assistantMsg.content.includes("I cannot find sufficient evidence")) {
              assistantMsg.is_unsupported_refusal = true;
            }

            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = { ...assistantMsg };
              return updated;
            });
          }
        }
      }
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "ASSISTANT",
          content: `Error connecting to Tutor: ${err.message}. Please verify the backend server is running.`,
        },
      ]);
    } finally {
      setIsStreaming(false);
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
            <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">Learning Partner</span>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Brain className="w-5 h-5 text-indigo-400" /> Grounded AI Tutor
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setInspectDrawerOpen(!inspectDrawerOpen)}
            className="text-xs bg-surface hover:bg-surface-raised border border-gray-700 text-gray-300 hover:text-white px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5"
          >
            <Eye className="w-3.5 h-3.5" /> Inspect AI Context
          </button>
          <Link
            href={`/projects/${projectId}/quiz`}
            className="bg-primary-600 hover:bg-primary-500 text-white text-xs font-medium px-4 py-2 rounded-lg transition-colors shadow-lg shadow-blue-500/20"
          >
            Take Adaptive Quiz
          </Link>
        </div>
      </header>

      {/* Chat Messages Stream */}
      <div className="flex-1 max-w-4xl w-full mx-auto px-6 py-8 overflow-y-auto space-y-6">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-4 ${msg.role === "USER" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "ASSISTANT" && (
              <div className="w-8 h-8 rounded-lg bg-indigo-950 border border-indigo-800 text-indigo-400 flex items-center justify-center shrink-0 mt-1">
                <Brain className="w-4 h-4" />
              </div>
            )}

            <div
              className={`max-w-2xl rounded-2xl p-5 ${
                msg.role === "USER"
                  ? "bg-primary-600 text-white rounded-br-none shadow-lg shadow-blue-500/10"
                  : msg.is_unsupported_refusal
                  ? "bg-amber-950/40 border border-amber-800 text-amber-200 rounded-bl-none"
                  : "bg-surface border border-gray-800 text-gray-100 rounded-bl-none shadow-md"
              }`}
            >
              {msg.is_unsupported_refusal && (
                <div className="flex items-center gap-2 text-amber-400 text-xs font-bold uppercase tracking-wider mb-2">
                  <AlertCircle className="w-4 h-4" /> Unsupported Question (Zero Hallucination Guard)
                </div>
              )}

              <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>

              {/* Tool Execution Widgets (PRD §8 Controlled Capabilities) */}
              {msg.tools_invoked && msg.tools_invoked.length > 0 && (
                <div className="mt-3 space-y-2">
                  {msg.tools_invoked.map((t, tIdx) => {
                    if (t.tool === "check_concept_mastery" && t.result) {
                      return (
                        <div key={tIdx} className="p-3 rounded-xl bg-surface-raised border border-cyan-800/80 flex items-center justify-between text-xs">
                          <div className="flex items-center gap-2.5">
                            <Award className="w-5 h-5 text-cyan-400 shrink-0" />
                            <div>
                              <div className="font-bold text-white">
                                {t.result.concept_name} (Mastery {t.result.mastery_score}%)
                              </div>
                              <div className="text-[11px] text-gray-400">
                                {t.result.total_attempts} attempts &bull; {t.result.consecutive_mistakes} consecutive errors
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-cyan-950 border border-cyan-800 text-cyan-300">
                              {t.result.trend_state}
                            </span>
                          </div>
                        </div>
                      );
                    }

                    if (t.tool === "trigger_remedial_quiz") {
                      return (
                        <div key={tIdx} className="p-3.5 rounded-xl bg-gradient-to-r from-amber-950/60 to-surface-raised border border-amber-800 flex items-center justify-between gap-4 text-xs shadow-lg shadow-amber-900/10">
                          <div className="flex items-center gap-2.5">
                            <Sparkles className="w-5 h-5 text-amber-400 shrink-0" />
                            <div>
                              <div className="font-bold text-amber-200">
                                Practice Quiz Prepared ({t.result?.concept_name || t.arguments?.concept_name || "Assessment"})
                              </div>
                              <p className="text-[11px] text-gray-300">
                                3 targeted adaptive questions are ready for you.
                              </p>
                            </div>
                          </div>
                          <Link
                            href={`/projects/${projectId}/quiz`}
                            className="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs whitespace-nowrap transition-colors flex items-center gap-1 shadow-md shadow-amber-500/10"
                          >
                            Launch Quiz &rarr;
                          </Link>
                        </div>
                      );
                    }

                    if (t.tool === "record_learner_preference") {
                      return (
                        <div key={tIdx} className="p-2.5 rounded-lg bg-surface-raised/80 border border-purple-800/60 text-xs text-purple-200 flex items-center gap-2">
                          <Brain className="w-3.5 h-3.5 text-purple-400" />
                          <span>Learner preference saved: &ldquo;{t.arguments?.preference}&rdquo;</span>
                        </div>
                      );
                    }

                    return (
                      <div key={tIdx} className="p-2 rounded bg-surface-raised text-[11px] text-gray-400 flex items-center gap-1.5">
                        <Activity className="w-3 h-3 text-cyan-400" /> Executed application tool: {t.tool}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Citations Badges */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-4 pt-3 border-t border-gray-800/80 flex flex-wrap gap-2">
                  <span className="text-[10px] uppercase font-bold text-gray-400 flex items-center gap-1">
                    <BookOpen className="w-3 h-3 text-blue-400" /> Grounded Original PDF Citations:
                  </span>
                  {msg.citations.map((c, cIdx) => (
                    <button
                      key={cIdx}
                      type="button"
                      onClick={() => openCitationInViewer(c)}
                      title={`Open original PDF directly at Page ${c.page_number}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-950/80 hover:bg-blue-900 border border-blue-800 text-blue-300 text-xs font-semibold cursor-pointer transition-all hover:scale-105 shadow-sm"
                    >
                      <BookOpen className="w-3.5 h-3.5 text-blue-400" />
                      <span>Original PDF &bull; Page {c.page_number} ({c.document_title})</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {msg.role === "USER" && (
              <div className="w-8 h-8 rounded-lg bg-blue-950 border border-blue-800 text-blue-400 flex items-center justify-center shrink-0 mt-1">
                <UserIcon className="w-4 h-4" />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Quick Prompt Chips */}
      <div className="max-w-4xl w-full mx-auto px-6 mb-2 flex flex-wrap gap-2">
        <button
          onClick={() => handleSend("What is my current mastery on neural optimization and can you quiz me?")}
          className="text-xs bg-cyan-950/80 border border-cyan-800 text-cyan-300 hover:bg-cyan-900 px-3 py-1 rounded-full transition-colors flex items-center gap-1.5 font-medium shadow-sm"
        >
          🎯 Check Mastery &amp; Quiz Me (Tool Calling)
        </button>
        <button
          onClick={() => handleSend("Explain the core formula of backpropagation with an analogy.")}
          className="text-xs bg-surface border border-gray-800 text-gray-400 hover:text-white hover:border-gray-700 px-3 py-1 rounded-full transition-colors"
        >
          💡 Explain with an analogy
        </button>
        <button
          onClick={() => handleSend("What happens when the learning rate is set too high?")}
          className="text-xs bg-surface border border-gray-800 text-gray-400 hover:text-white hover:border-gray-700 px-3 py-1 rounded-full transition-colors"
        >
          ⚠️ Risk of high learning rate
        </button>
        <button
          onClick={() => handleSend("How do I bake a chocolate cake?")}
          className="text-xs bg-surface border border-gray-800 text-amber-400/80 hover:text-amber-300 hover:border-amber-800 px-3 py-1 rounded-full transition-colors"
        >
          🧪 Test Unsupported Refusal
        </button>
      </div>

      {/* Chat Input Bar */}
      <div className="border-t border-gray-800 bg-surface/50 backdrop-blur p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="max-w-4xl mx-auto flex items-center gap-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isStreaming}
            placeholder="Ask a question grounded in your project notes..."
            className="flex-1 px-5 py-3 rounded-xl bg-surface-raised border border-gray-700 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-primary-500 transition-colors"
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="p-3 bg-primary-600 hover:bg-primary-500 text-white rounded-xl transition-all disabled:opacity-50 shadow-lg shadow-blue-500/20"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>

      {/* Inspect AI Context Slide-over Drawer */}
      {inspectDrawerOpen && (
        <div className="fixed inset-y-0 right-0 w-96 bg-surface border-l border-gray-800 shadow-2xl p-6 z-50 overflow-y-auto">
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-gray-800">
            <h3 className="font-bold text-white text-base flex items-center gap-2">
              <Info className="w-4 h-4 text-blue-400" /> Retrieved Context Chunks
            </h3>
            <button
              onClick={() => setInspectDrawerOpen(false)}
              className="text-gray-400 hover:text-white text-xs"
            >
              Close
            </button>
          </div>

          <div className="space-y-4">
            {activeCitations.length === 0 ? (
              <p className="text-xs text-gray-500">
                Ask a question to see the retrieved project chunks and similarity metadata.
              </p>
            ) : (
              activeCitations.map((c, i) => (
                <div key={i} className="p-4 rounded-lg bg-surface-raised border border-gray-700/50">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-blue-400">{c.document_title}</span>
                    <span className="text-[10px] font-semibold bg-gray-800 text-gray-300 px-2 py-0.5 rounded">
                      Page {c.page_number}
                    </span>
                  </div>
                  <p className="text-xs text-gray-300 italic line-clamp-4">
                    &ldquo;{c.snippet}&rdquo;
                  </p>
                  <button
                    onClick={() => openCitationInViewer(c)}
                    className="mt-2.5 text-[11px] text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1.5 transition-colors"
                  >
                    <BookOpen className="w-3.5 h-3.5" /> Open in Original PDF (Page {c.page_number}) &rarr;
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* In-Browser Document Viewer Modal */}
      {activeViewer?.isOpen && (
        <DocumentViewerModal
          projectId={projectId}
          materialId={activeViewer.materialId}
          documentTitle={activeViewer.documentTitle}
          initialPage={activeViewer.initialPage}
          highlightSnippet={activeViewer.highlightSnippet}
          onClose={() => setActiveViewer(null)}
        />
      )}
    </div>
  );
}
