"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ArrowRight,
  HelpCircle,
  Award,
  TrendingUp,
  RefreshCw,
  BookOpen,
  MessageSquare,
  BarChart3,
  Layers,
  Check
} from "lucide-react";
import { ApiClient } from "@/lib/api";
import {
  Question,
  QuizStartResponse,
  AnswerEvaluation,
  NextQuestionResponse,
  QuizCompletionResults,
  MasteryDelta
} from "@/types";

type QuizPhase = "CONFIG" | "QUESTION_ACTIVE" | "QUESTION_EVALUATED" | "COMPLETED";

export default function AdaptiveQuizPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  // Session & Phase State
  const [phase, setPhase] = useState<QuizPhase>("CONFIG");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Config State
  const [questionCount, setQuestionCount] = useState<number>(5);
  const [questionTypeFilter, setQuestionTypeFilter] = useState<"ALL" | "MCQ" | "OPEN_ENDED">("ALL");

  // Running Quiz State
  const [quizId, setQuizId] = useState<string | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [questionNumber, setQuestionNumber] = useState<number>(1);
  const [totalQuestions, setTotalQuestions] = useState<number>(5);
  const [userAnswer, setUserAnswer] = useState<string>("");
  const [evaluation, setEvaluation] = useState<AnswerEvaluation | null>(null);

  // Completion State
  const [results, setResults] = useState<QuizCompletionResults | null>(null);

  // Restore active quiz on page refresh if saved
  useEffect(() => {
    const savedQuizId = localStorage.getItem(`active_quiz_${projectId}`);
    if (savedQuizId) {
      resumeQuiz(savedQuizId);
    }
  }, [projectId]);

  const resumeQuiz = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const state = await ApiClient.request<any>(`/quizzes/${id}`);
      if (state.status === "COMPLETED") {
        const res = await ApiClient.request<QuizCompletionResults>(`/quizzes/${id}/results`);
        setQuizId(id);
        setResults(res);
        setPhase("COMPLETED");
        localStorage.removeItem(`active_quiz_${projectId}`);
      } else if (state.current_question) {
        setQuizId(id);
        setTotalQuestions(state.total_questions);
        setQuestionNumber(state.completed_questions + 1);
        setCurrentQuestion(state.current_question);
        setUserAnswer("");
        setEvaluation(null);
        setPhase("QUESTION_ACTIVE");
      }
    } catch (err: any) {
      console.warn("Could not resume quiz:", err);
      localStorage.removeItem(`active_quiz_${projectId}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStartQuiz = async () => {
    setLoading(true);
    setError(null);
    try {
      const payloadTypes =
        questionTypeFilter === "ALL"
          ? ["MCQ", "OPEN_ENDED"]
          : [questionTypeFilter];

      const res = await ApiClient.request<QuizStartResponse>(`/projects/${projectId}/quizzes`, {
        method: "POST",
        body: JSON.stringify({
          question_count: questionCount,
          question_types: payloadTypes,
        }),
      });

      setQuizId(res.quiz_id);
      localStorage.setItem(`active_quiz_${projectId}`, res.quiz_id);
      setCurrentQuestion(res.question);
      setQuestionNumber(res.question_number);
      setTotalQuestions(res.total_questions);
      setUserAnswer("");
      setEvaluation(null);
      setPhase("QUESTION_ACTIVE");
    } catch (err: any) {
      setError(err.message || "Failed to start adaptive quiz");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitAnswer = async () => {
    if (!quizId || !currentQuestion || !userAnswer.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const evalRes = await ApiClient.request<AnswerEvaluation>(
        `/quizzes/${quizId}/questions/${currentQuestion.id}/answer`,
        {
          method: "POST",
          body: JSON.stringify({ user_answer: userAnswer.trim() }),
        }
      );

      setEvaluation(evalRes);
      setPhase("QUESTION_EVALUATED");
    } catch (err: any) {
      setError(err.message || "Failed to submit answer");
    } finally {
      setLoading(false);
    }
  };

  const handleNextQuestion = async () => {
    if (!quizId) return;

    setLoading(true);
    setError(null);
    try {
      const nextRes = await ApiClient.request<NextQuestionResponse>(`/quizzes/${quizId}/next`, {
        method: "POST",
      });

      if (nextRes.is_completed || !nextRes.question) {
        // Quiz completed! Fetch finalized results
        const finalResults = await ApiClient.request<QuizCompletionResults>(`/quizzes/${quizId}/complete`, {
          method: "POST",
        });
        localStorage.removeItem(`active_quiz_${projectId}`);
        setResults(finalResults);
        setPhase("COMPLETED");
      } else {
        setCurrentQuestion(nextRes.question);
        setQuestionNumber(nextRes.question_number);
        setTotalQuestions(nextRes.total_questions);
        setUserAnswer("");
        setEvaluation(null);
        setPhase("QUESTION_ACTIVE");
      }
    } catch (err: any) {
      setError(err.message || "Failed to advance to next question");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    localStorage.removeItem(`active_quiz_${projectId}`);
    setQuizId(null);
    setCurrentQuestion(null);
    setUserAnswer("");
    setEvaluation(null);
    setResults(null);
    setPhase("CONFIG");
  };

  const progressPercent = Math.min(
    100,
    Math.round(((questionNumber - 1) / totalQuestions) * 100)
  );

  return (
    <div className="min-h-screen bg-background text-gray-100 flex flex-col selection:bg-primary-500/30">
      {/* Navigation Header */}
      <header className="border-b border-gray-800 bg-surface/80 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-4">
          <Link
            href={`/projects/${projectId}`}
            className="text-gray-400 hover:text-white p-2 rounded-xl hover:bg-gray-800/60 transition-colors border border-transparent hover:border-gray-700"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 bg-amber-950/40 border border-amber-800/40 px-2 py-0.5 rounded">
                Adaptive Assessment
              </span>
              <span className="text-xs text-gray-500 font-mono">Strict Project Isolation</span>
            </div>
            <h1 className="text-lg font-bold text-white flex items-center gap-2 mt-0.5">
              <Sparkles className="w-4 h-4 text-amber-400" /> Evidence-Based Learning Assessment
            </h1>
          </div>
        </div>

        {phase !== "CONFIG" && (
          <button
            onClick={handleReset}
            className="text-xs text-gray-400 hover:text-gray-200 border border-gray-700 hover:border-gray-600 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Start New Quiz
          </button>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-3xl w-full mx-auto px-6 py-8 flex flex-col justify-center">
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-rose-950/50 border border-rose-800/60 text-rose-300 text-xs flex items-center gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400" />
            <span className="flex-1">{error}</span>
          </div>
        )}

        {/* ========================================================================= */}
        {/* PHASE 1: CONFIGURATION / INTRO */}
        {/* ========================================================================= */}
        {phase === "CONFIG" && (
          <div className="p-8 sm:p-10 rounded-2xl bg-surface border border-gray-800 shadow-2xl space-y-8 animate-in fade-in zoom-in-95 duration-200">
            <div className="text-center max-w-lg mx-auto space-y-3">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-amber-500/20 to-primary-500/20 border border-amber-500/30 text-amber-400 mx-auto flex items-center justify-center shadow-lg shadow-amber-500/10">
                <Sparkles className="w-8 h-8" />
              </div>
              <h2 className="text-2xl font-extrabold text-white tracking-tight">
                Adaptive Learning Assessment
              </h2>
              <p className="text-xs sm:text-sm text-gray-400 leading-relaxed">
                Rather than random questions, the assessment engine analyzes your current concept mastery, recent mistake patterns, and evidence uncertainty. Questions are grounded strictly in this project&apos;s ingested materials.
              </p>
            </div>

            {/* Quiz Parameters */}
            <div className="grid sm:grid-cols-2 gap-6 pt-2">
              {/* Question Count Selection */}
              <div className="space-y-3 p-4 rounded-xl bg-surface-raised border border-gray-800">
                <label className="text-xs font-bold text-gray-300 uppercase tracking-wider block">
                  Questions in Session
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[3, 5, 10].map((count) => (
                    <button
                      key={count}
                      type="button"
                      onClick={() => setQuestionCount(count)}
                      className={`py-2 px-3 rounded-lg text-xs font-bold transition-all border ${
                        questionCount === count
                          ? "bg-primary-600 border-primary-400 text-white shadow-md shadow-primary-500/20"
                          : "bg-surface border-gray-700 text-gray-300 hover:border-gray-600"
                      }`}
                    >
                      {count} Questions
                    </button>
                  ))}
                </div>
              </div>

              {/* Question Types Selection */}
              <div className="space-y-3 p-4 rounded-xl bg-surface-raised border border-gray-800">
                <label className="text-xs font-bold text-gray-300 uppercase tracking-wider block">
                  Question Format
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: "ALL", label: "Mixed" },
                    { id: "MCQ", label: "MCQ Only" },
                    { id: "OPEN_ENDED", label: "Open-Ended" },
                  ].map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setQuestionTypeFilter(t.id as any)}
                      className={`py-2 px-2 rounded-lg text-xs font-bold transition-all border ${
                        questionTypeFilter === t.id
                          ? "bg-amber-600 border-amber-400 text-white shadow-md shadow-amber-500/20"
                          : "bg-surface border-gray-700 text-gray-300 hover:border-gray-600"
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Pedagogical Guarantees Banner */}
            <div className="p-4 rounded-xl bg-blue-950/20 border border-blue-900/40 text-xs text-gray-300 space-y-2">
              <span className="font-bold text-blue-300 uppercase text-[10px] tracking-wider flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5" /> How Adaptation Works
              </span>
              <ul className="space-y-1 text-gray-400 text-[11px] list-disc list-inside">
                <li>Concepts needing reinforcement are prioritized dynamically based on evidence gap.</li>
                <li>Difficulty adapts to accumulated proof (never simple right = hard, wrong = easy).</li>
                <li>Open-ended explanations are graded by Gemini 2.5 Flash on multi-factor rubrics.</li>
              </ul>
            </div>

            <div className="pt-2 text-center">
              <button
                onClick={handleStartQuiz}
                disabled={loading}
                className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-gradient-to-r from-primary-600 to-indigo-600 hover:from-primary-500 hover:to-indigo-500 text-white font-semibold text-sm shadow-xl shadow-primary-600/20 transition-all flex items-center justify-center gap-2 mx-auto disabled:opacity-50"
              >
                {loading ? "Synthesizing Grounded Question 1..." : "Start Adaptive Quiz"}
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* PHASE 2 & 3: ACTIVE QUESTION OR EVALUATED QUESTION */}
        {/* ========================================================================= */}
        {(phase === "QUESTION_ACTIVE" || phase === "QUESTION_EVALUATED") && currentQuestion && (
          <div className="space-y-6">
            {/* Top Progress & Concept Meta Bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-gray-300 flex items-center gap-2">
                  <span>Question {questionNumber} of {totalQuestions}</span>
                  <span className="text-gray-600">•</span>
                  <span className="text-amber-400 font-medium">
                    {currentQuestion.concept_name || "Target Concept"}
                  </span>
                </span>
                <span
                  className={`text-[10px] uppercase font-extrabold px-2.5 py-0.5 rounded-full border ${
                    currentQuestion.difficulty === "EASY"
                      ? "bg-emerald-950/60 border-emerald-800/60 text-emerald-400"
                      : currentQuestion.difficulty === "HARD"
                      ? "bg-purple-950/60 border-purple-800/60 text-purple-400"
                      : "bg-blue-950/60 border-blue-800/60 text-blue-400"
                  }`}
                >
                  Difficulty: {currentQuestion.difficulty}
                </span>
              </div>

              {/* Animated Progress Bar */}
              <div className="w-full h-1.5 rounded-full bg-gray-800 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary-500 to-amber-500 transition-all duration-300 rounded-full"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>

            {/* Question Card */}
            <div className="p-6 sm:p-8 rounded-2xl bg-surface border border-gray-800 shadow-xl space-y-6">
              <div className="space-y-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
                  {currentQuestion.question_type === "MCQ"
                    ? "Multiple Choice Question"
                    : "Conceptual Synthesis (Open-Ended)"}
                </span>
                <p className="text-base sm:text-lg font-medium text-white leading-relaxed">
                  {currentQuestion.prompt}
                </p>
              </div>

              {/* MCQ Options */}
              {currentQuestion.question_type === "MCQ" ? (
                <div className="space-y-3 pt-2">
                  {currentQuestion.options?.map((opt) => {
                    const isSelected = userAnswer === opt.key;
                    const isEvaluated = phase === "QUESTION_EVALUATED";
                    const isCorrectOption = evaluation?.correct_answer === opt.key;

                    let cardClass = "border-gray-800 bg-surface-raised text-gray-300 hover:border-gray-700";
                    if (isEvaluated) {
                      if (isCorrectOption) {
                        cardClass = "border-emerald-600 bg-emerald-950/40 text-emerald-200";
                      } else if (isSelected && !evaluation?.is_correct) {
                        cardClass = "border-rose-600 bg-rose-950/40 text-rose-200";
                      } else {
                        cardClass = "border-gray-800/50 bg-surface-raised/40 text-gray-500 opacity-60";
                      }
                    } else if (isSelected) {
                      cardClass = "border-primary-500 bg-primary-950/40 text-white ring-1 ring-primary-500";
                    }

                    return (
                      <label
                        key={opt.key}
                        className={`flex items-start gap-4 p-4 rounded-xl border transition-all cursor-pointer ${cardClass}`}
                      >
                        <input
                          type="radio"
                          name={currentQuestion.id}
                          value={opt.key}
                          disabled={isEvaluated}
                          checked={isSelected}
                          onChange={() => setUserAnswer(opt.key)}
                          className="mt-1 text-primary-600 focus:ring-primary-500"
                        />
                        <div className="text-xs sm:text-sm leading-relaxed flex-1">
                          <strong className="text-gray-200 font-bold mr-1.5">{opt.key}.</strong>
                          {opt.text}
                        </div>
                        {isEvaluated && isCorrectOption && (
                          <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                        )}
                        {isEvaluated && isSelected && !evaluation?.is_correct && (
                          <XCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
                        )}
                      </label>
                    );
                  })}
                </div>
              ) : (
                /* Open-Ended Textarea */
                <div className="space-y-2 pt-2">
                  <div className="flex items-center justify-between text-[11px] text-gray-400">
                    <span>Explain mechanisms, trade-offs, and practical application:</span>
                    <span>{userAnswer.length} characters</span>
                  </div>
                  <textarea
                    rows={5}
                    value={userAnswer}
                    disabled={phase === "QUESTION_EVALUATED"}
                    onChange={(e) => setUserAnswer(e.target.value)}
                    placeholder="Provide a technically precise explanation covering the core mechanism, primary advantages, and realistic scenarios..."
                    className="w-full p-4 rounded-xl bg-surface-raised border border-gray-700/80 text-white text-sm focus:outline-none focus:border-primary-500 leading-relaxed placeholder:text-gray-600"
                  />
                </div>
              )}

              {/* Submit Button (Only visible during active question phase) */}
              {phase === "QUESTION_ACTIVE" && (
                <div className="flex justify-end pt-4 border-t border-gray-800/80">
                  <button
                    onClick={handleSubmitAnswer}
                    disabled={loading || !userAnswer.trim()}
                    className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition-all flex items-center gap-2 shadow-lg shadow-emerald-600/20 disabled:opacity-50"
                  >
                    {loading ? "Evaluating Rubrics..." : "Submit Answer"}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>

            {/* ========================================================================= */}
            {/* IMMEDIATE DIAGNOSTIC FEEDBACK (Phase: QUESTION_EVALUATED) */}
            {/* ========================================================================= */}
            {phase === "QUESTION_EVALUATED" && evaluation && (
              <div className="p-6 sm:p-8 rounded-2xl bg-surface border border-gray-800 shadow-2xl space-y-6 animate-in fade-in duration-300">
                {/* Result Header Badge */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    {evaluation.is_correct ? (
                      <div className="p-2 rounded-lg bg-emerald-950/80 text-emerald-400 border border-emerald-800">
                        <CheckCircle2 className="w-5 h-5" />
                      </div>
                    ) : (
                      <div className="p-2 rounded-lg bg-rose-950/80 text-rose-400 border border-rose-800">
                        <XCircle className="w-5 h-5" />
                      </div>
                    )}
                    <div>
                      <h3 className="text-sm font-bold text-white">
                        {evaluation.is_correct ? "Accurate Understanding" : "Conceptual Gap Detected"}
                      </h3>
                      <p className="text-xs text-gray-400">
                        Score: {Math.round(evaluation.score * 100)}%
                      </p>
                    </div>
                  </div>

                  {/* Concept Mastery Shift Pill */}
                  {evaluation.concept_mastery_before !== undefined && evaluation.concept_mastery_after !== undefined && (
                    <div className="p-2.5 rounded-xl bg-surface-raised border border-gray-700/60 text-right">
                      <span className="text-[10px] uppercase font-bold text-gray-400 block">
                        Mastery Shift
                      </span>
                      <span className="text-xs font-bold text-white flex items-center gap-1">
                        <span className="text-gray-400">{evaluation.concept_mastery_before}%</span>
                        <ArrowRight className="w-3 h-3 text-gray-500" />
                        <span className={evaluation.concept_mastery_after >= evaluation.concept_mastery_before ? "text-emerald-400" : "text-rose-400"}>
                          {evaluation.concept_mastery_after}%
                        </span>
                      </span>
                    </div>
                  )}
                </div>

                {/* Open-Ended Multi-Factor Rubric Gauges */}
                {evaluation.evaluation && (evaluation.evaluation.understanding !== undefined) && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 rounded-xl bg-surface-raised border border-gray-800">
                    {[
                      { label: "Understanding", val: evaluation.evaluation.understanding },
                      { label: "Accuracy", val: evaluation.evaluation.accuracy },
                      { label: "Relevance", val: evaluation.evaluation.relevance },
                      { label: "Reasoning", val: evaluation.evaluation.reasoning },
                    ].map((m) => (
                      <div key={m.label} className="space-y-1 text-center">
                        <span className="text-[10px] uppercase font-bold text-gray-400">{m.label}</span>
                        <div className="text-sm font-extrabold text-white">
                          {Math.round((m.val || 0) * 100)}%
                        </div>
                        <div className="w-full h-1 rounded-full bg-gray-800 overflow-hidden">
                          <div
                            className="h-full bg-blue-500 rounded-full"
                            style={{ width: `${Math.round((m.val || 0) * 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Diagnostic Feedback Breakdown */}
                <div className="p-4 rounded-xl bg-surface-raised border border-gray-800 space-y-3 text-xs leading-relaxed">
                  <div className="whitespace-pre-line text-gray-300">
                    {evaluation.feedback}
                  </div>
                </div>

                {/* Advance Button */}
                <div className="flex justify-end pt-2">
                  <button
                    onClick={handleNextQuestion}
                    disabled={loading}
                    className="px-7 py-3 rounded-xl bg-primary-600 hover:bg-primary-500 text-white font-semibold text-xs transition-all flex items-center gap-2 shadow-lg shadow-primary-600/20 disabled:opacity-50"
                  >
                    {loading ? (
                      "Synthesizing Next Adaptation..."
                    ) : questionNumber >= totalQuestions ? (
                      <>Complete Assessment &amp; View Growth <ArrowRight className="w-4 h-4" /></>
                    ) : (
                      <>Next Question <ArrowRight className="w-4 h-4" /></>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ========================================================================= */}
        {/* PHASE 4: QUIZ COMPLETION & GROWTH DASHBOARD */}
        {/* ========================================================================= */}
        {phase === "COMPLETED" && results && (
          <div className="space-y-8 animate-in fade-in duration-300">
            {/* Hero Score Card */}
            <div className="p-8 sm:p-10 rounded-2xl bg-surface border border-gray-800 shadow-2xl text-center space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-emerald-500/20 to-primary-500/20 border border-emerald-500/30 text-emerald-400 mx-auto flex items-center justify-center shadow-lg shadow-emerald-500/10">
                <Award className="w-8 h-8" />
              </div>
              <h2 className="text-3xl font-extrabold text-white tracking-tight">
                {results.score}% Overall Score
              </h2>
              <p className="text-xs sm:text-sm text-gray-400 max-w-md mx-auto leading-relaxed">
                Adaptive assessment completed. Your Concept Mastery values, Growth trajectories, and Mistake logs have been updated automatically.
              </p>

              {/* Stats Bar */}
              <div className="grid grid-cols-3 gap-3 max-w-md mx-auto pt-2">
                <div className="p-3 rounded-xl bg-surface-raised border border-gray-800">
                  <span className="text-[10px] uppercase font-bold text-gray-400 block">Attempted</span>
                  <span className="text-base font-extrabold text-white">{results.questions_attempted}</span>
                </div>
                <div className="p-3 rounded-xl bg-surface-raised border border-gray-800">
                  <span className="text-[10px] uppercase font-bold text-gray-400 block">Correct</span>
                  <span className="text-base font-extrabold text-emerald-400">{results.questions_correct}</span>
                </div>
                <div className="p-3 rounded-xl bg-surface-raised border border-gray-800">
                  <span className="text-[10px] uppercase font-bold text-gray-400 block">Concepts</span>
                  <span className="text-base font-extrabold text-blue-400">{results.concepts_assessed}</span>
                </div>
              </div>
            </div>

            {/* Strengths & Attention Areas */}
            <div className="grid sm:grid-cols-2 gap-6">
              {/* Strengths */}
              <div className="p-5 rounded-xl bg-surface border border-gray-800 shadow-md space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-400">
                  <Check className="w-4 h-4" /> Demonstrated Strengths
                </div>
                {results.strengths.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {results.strengths.map((s) => (
                      <span
                        key={s}
                        className="px-3 py-1 rounded-lg bg-emerald-950/50 border border-emerald-800/60 text-emerald-300 text-xs font-semibold"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-500 italic">No concepts met the 75% threshold this round.</p>
                )}
              </div>

              {/* Attention Areas */}
              <div className="p-5 rounded-xl bg-surface border border-gray-800 shadow-md space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-400">
                  <AlertCircle className="w-4 h-4" /> Focus &amp; Attention Areas
                </div>
                {results.attention_areas.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {results.attention_areas.map((a) => (
                      <span
                        key={a}
                        className="px-3 py-1 rounded-lg bg-amber-950/50 border border-amber-800/60 text-amber-300 text-xs font-semibold"
                      >
                        {a}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-500 italic">No critical attention areas detected!</p>
                )}
              </div>
            </div>

            {/* Concept Mastery Trajectory Changes */}
            {results.mastery_changes.length > 0 && (
              <div className="p-6 rounded-xl bg-surface border border-gray-800 shadow-md space-y-4">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-gray-300">
                  <TrendingUp className="w-4 h-4 text-primary-400" /> Concept Mastery Trajectory (Before vs After)
                </div>
                <div className="space-y-3">
                  {results.mastery_changes.map((mc) => (
                    <div
                      key={mc.concept_id}
                      className="p-3 rounded-lg bg-surface-raised border border-gray-800 flex items-center justify-between text-xs"
                    >
                      <span className="font-bold text-white">{mc.concept_name}</span>
                      <div className="flex items-center gap-3 font-mono">
                        <span className="text-gray-400">{mc.before}%</span>
                        <ArrowRight className="w-3.5 h-3.5 text-gray-600" />
                        <span className="font-bold text-white">{mc.after}%</span>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                            mc.delta >= 0
                              ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                              : "bg-rose-950 text-rose-400 border border-rose-800"
                          }`}
                        >
                          {mc.delta >= 0 ? `+${mc.delta}%` : `${mc.delta}%`}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actionable Next Step Recommendation */}
            {results.recommendation && (
              <div className="p-6 rounded-xl bg-gradient-to-r from-blue-950/40 to-indigo-950/30 border border-blue-800/60 shadow-lg space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-blue-300">
                  <Sparkles className="w-4 h-4 text-blue-400" /> Recommended Action
                </div>
                <p className="text-xs sm:text-sm text-gray-200 leading-relaxed font-medium">
                  {results.recommendation}
                </p>
                <div className="pt-2 flex flex-wrap items-center gap-3">
                  <Link
                    href={`/projects/${projectId}/materials`}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition-colors"
                  >
                    <BookOpen className="w-3.5 h-3.5" /> Review Project Materials
                  </Link>
                  <Link
                    href={`/projects/${projectId}/tutor`}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-surface-raised hover:bg-gray-800 border border-gray-700 text-gray-200 text-xs font-semibold transition-colors"
                  >
                    <MessageSquare className="w-3.5 h-3.5" /> Ask AI Tutor
                  </Link>
                </div>
              </div>
            )}

            {/* Navigation Footers */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-gray-800">
              <button
                onClick={handleReset}
                className="px-5 py-2.5 rounded-xl border border-gray-700 hover:border-gray-600 text-gray-300 text-xs font-bold transition-colors flex items-center gap-2"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Retake Another Adaptive Quiz
              </button>
              <Link
                href={`/projects/${projectId}/mastery`}
                className="px-6 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-bold transition-all shadow-lg shadow-primary-600/20 flex items-center gap-2"
              >
                <BarChart3 className="w-3.5 h-3.5" /> Inspect Updated Mastery &amp; Growth <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
