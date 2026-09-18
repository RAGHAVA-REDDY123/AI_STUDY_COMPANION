import Link from "next/link";
import { BookOpen, Sparkles, Brain, Award, ShieldCheck, ArrowRight } from "lucide-react";

export default function HomePage() {
  return (
    <main className="flex flex-col min-h-screen">
      {/* Header */}
      <header className="border-b border-gray-800 bg-surface/50 backdrop-blur px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-primary-600 p-2 rounded-lg text-white">
            <Brain className="w-6 h-6" />
          </div>
          <span className="font-bold text-xl tracking-tight text-white">AI Study Companion</span>
        </div>
        <div className="flex items-center gap-4">
          <Link
            href="/login"
            className="text-sm font-medium text-gray-300 hover:text-white transition-colors"
          >
            Sign In
          </Link>
          <Link
            href="/dashboard"
            className="text-sm font-medium bg-primary-600 hover:bg-primary-500 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
          >
            Open Workspace <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center px-6 text-center max-w-4xl mx-auto py-20">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-950/60 border border-blue-800 text-blue-400 text-xs font-semibold uppercase tracking-wider mb-6">
          <Sparkles className="w-3.5 h-3.5" /> Candidate Challenge Prototype v3.0
        </div>
        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white mb-6 leading-tight">
          A Persistent, Contextual &amp; <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400">Measurable AI Learning Companion</span>
        </h1>
        <p className="text-lg text-gray-400 max-w-2xl mb-10">
          Move beyond superficial chatbots. Upload your study notes, learn with a grounded AI Tutor with page citations, take adaptive quizzes with rubric feedback, and continuously track concept mastery.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/dashboard"
            className="bg-primary-600 hover:bg-primary-500 text-white font-medium px-6 py-3 rounded-lg transition-all flex items-center gap-2 text-base shadow-lg shadow-blue-500/20"
          >
            Enter Learning Workspace <ArrowRight className="w-5 h-5" />
          </Link>
          <Link
            href="/admin"
            className="bg-surface hover:bg-surface-raised border border-gray-800 text-gray-300 font-medium px-6 py-3 rounded-lg transition-all text-base"
          >
            Admin Observability Dashboard
          </Link>
        </div>

        {/* Learning Loop Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 text-left w-full">
          <div className="p-6 rounded-xl bg-surface border border-gray-800">
            <BookOpen className="w-8 h-8 text-blue-400 mb-4" />
            <h3 className="font-semibold text-lg text-white mb-2">1. Grounded RAG &amp; Citations</h3>
            <p className="text-sm text-gray-400">Strictly cites source documents with exact page numbers. Rejects unsupported queries with zero hallucinations.</p>
          </div>
          <div className="p-6 rounded-xl bg-surface border border-gray-800">
            <Brain className="w-8 h-8 text-indigo-400 mb-4" />
            <h3 className="font-semibold text-lg text-white mb-2">2. Adaptive Quiz &amp; Rubrics</h3>
            <p className="text-sm text-gray-400">Tests understanding via dynamic MCQs and open-ended questions evaluated on multi-factor rubrics.</p>
          </div>
          <div className="p-6 rounded-xl bg-surface border border-gray-800">
            <Award className="w-8 h-8 text-emerald-400 mb-4" />
            <h3 className="font-semibold text-lg text-white mb-2">3. Mastery &amp; Next Action</h3>
            <p className="text-sm text-gray-400">Measures concept mastery percentages and growth states, answering &ldquo;What should I do next?&rdquo; with precision.</p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-6 text-center text-xs text-gray-500">
        AI Study Companion — Full Stack AI Engineer Candidate Prototype
      </footer>
    </main>
  );
}
