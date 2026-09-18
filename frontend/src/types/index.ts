export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'LEARNER' | 'ADMIN';
  is_active: boolean;
}

export interface Space {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  visual_tag: string;
  created_at: string;
}

export interface Project {
  id: string;
  space_id: string;
  name: string;
  description?: string;
  learning_goal: string;
  created_at: string;
}

export interface ProjectSummary {
  id: string;
  name: string;
  learning_goal: string;
  total_materials: number;
  total_concepts: number;
  average_mastery: number;
  active_recommendation?: {
    id: string;
    title: string;
    reasoning: string;
    action_type: string;
    target_payload: Record<string, any>;
  };
}

export interface Material {
  id: string;
  filename: string;
  file_size_bytes: number;
  total_pages: number;
  status: 'QUEUED' | 'PROCESSING' | 'READY' | 'FAILED';
  error_message?: string;
  created_at: string;
}

export interface Concept {
  id: string;
  name: string;
  description: string;
  importance_score: number;
}

export interface Citation {
  material_id?: string;
  document_title: string;
  page_number: number;
  snippet: string;
  is_verified?: boolean;
}

export interface ToolInvocation {
  tool: string;
  arguments?: Record<string, any>;
  result?: Record<string, any>;
}

export interface Message {
  id?: string;
  role: 'USER' | 'ASSISTANT' | 'SYSTEM';
  content: string;
  citations?: Citation[];
  tools_invoked?: ToolInvocation[];
  is_unsupported_refusal?: boolean;
}

export interface Question {
  id: string;
  quiz_id: string;
  concept_id?: string;
  concept_name?: string;
  question_type: 'MCQ' | 'OPEN_ENDED';
  difficulty: 'EASY' | 'MEDIUM' | 'HARD';
  question_order?: number;
  prompt: string;
  options?: { key: string; text: string }[];
}

export interface QuizStartResponse {
  quiz_id: string;
  question_number: number;
  total_questions: number;
  question: Question;
}

export interface AnswerEvaluation {
  question_id: string;
  is_correct: boolean;
  score: number;
  correct_answer: string;
  explanation: string;
  feedback: string;
  evaluation: {
    understanding?: number;
    accuracy?: number;
    relevance?: number;
    reasoning?: number;
    key_concepts_covered?: string[];
    missing_concepts?: string[];
    overall_score?: number;
    feedback?: string;
  };
  concept_name?: string;
  concept_mastery_before?: number;
  concept_mastery_after?: number;
}

export interface NextQuestionResponse {
  quiz_id: string;
  question_number: number;
  total_questions: number;
  is_completed: boolean;
  question?: Question;
}

export interface MasteryDelta {
  concept_id: string;
  concept_name: string;
  before: number;
  after: number;
  delta: number;
}

export interface QuizCompletionResults {
  quiz_id: string;
  project_id: string;
  status: string;
  score: number;
  questions_attempted: number;
  questions_correct: number;
  concepts_assessed: number;
  strengths: string[];
  attention_areas: string[];
  mastery_changes: MasteryDelta[];
  recommendation?: string;
  recommendation_action?: string;
  recommendation_id?: string;
}

export interface ConceptMastery {
  id: string;
  concept_id: string;
  concept_name: string;
  mastery_score: number;
  trend_state: 'IMPROVING' | 'STABLE' | 'REQUIRING_ATTENTION';
  total_attempts: number;
  consecutive_mistakes: number;
  last_assessed_at?: string;
}

export interface Recommendation {
  id: string;
  title: string;
  reasoning: string;
  action_type: 'REVIEW_MATERIAL' | 'TAKE_QUIZ' | 'REVISE_CONCEPT';
  target_payload: Record<string, any>;
  status: 'PENDING' | 'ACCEPTED' | 'DISMISSED';
}

export interface AdminPlatformStatsOut {
  total_users: number;
  total_spaces: number;
  total_projects: number;
  total_materials: number;
  total_ai_tokens: number;
  total_estimated_cost_usd: number;
  active_background_jobs: number;
  failed_background_jobs: number;
}

export interface AIUsageOut {
  id: string;
  request_id?: string;
  user_id?: string;
  project_id?: string;
  feature: string;
  operation?: string;
  provider?: string;
  model_name: string;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  latency_ms: number;
  estimated_cost_usd?: number;
  status_code: string;
  error_type?: string;
  error_details?: string;
  prompt_version?: string;
  metadata_json?: Record<string, any>;
  created_at: string;
}

export interface AIOverviewOut {
  total_requests: number;
  success_requests: number;
  failed_requests: number;
  success_rate: number;
  avg_latency_ms: number;
  total_tokens: number;
  total_estimated_cost_usd: number;
  requests_by_feature: Record<string, number>;
  requests_by_model: Record<string, number>;
  errors_by_type: Record<string, number>;
  requests_over_time: Array<{
    time: string;
    tokens: number;
    latency_ms: number;
    feature: string;
    status: string;
  }>;
  latency_distribution: Array<{
    request_id: string;
    feature: string;
    latency_ms: number;
    model: string;
  }>;
}

export interface RetrievalLogOut {
  id: string;
  request_id: string;
  project_id: string;
  user_id?: string;
  query: string;
  retrieval_method: string;
  top_k: number;
  final_k: number;
  retrieved_chunk_ids: any[];
  similarity_scores: Record<string, number>;
  retrieval_latency_ms: number;
  reranking_latency_ms: number;
  final_chunk_ids: any[];
  has_sufficient_evidence: boolean;
  retrieval_version: string;
  created_at: string;
}

export interface AIEvaluationResultOut {
  id: string;
  run_id: string;
  case_id: string;
  feature: string;
  input_data: Record<string, any>;
  expected_output: Record<string, any>;
  actual_output: Record<string, any>;
  score: number;
  passed: boolean;
  metrics: Record<string, any>;
  failure_reason?: string;
  created_at: string;
}

export interface AIEvaluationRunOut {
  id: string;
  run_name: string;
  evaluation_type: string;
  model: string;
  prompt_version?: string;
  retrieval_version?: string;
  status: string;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  metrics: Record<string, any>;
  created_at: string;
}

export interface AIEvaluationRunDetailOut extends AIEvaluationRunOut {
  results: AIEvaluationResultOut[];
}

export interface BackgroundJobOut {
  id: string;
  job_type: string;
  entity_id: string;
  idempotency_key: string;
  status: string;
  attempts: number;
  last_error?: string;
  created_at: string;
}

// --- Analytics Interfaces ---

export interface MasteryTimelinePoint {
  date: string;
  concept_name: string;
  score: number;
}

export interface QuizHistoryPoint {
  quiz_id: string;
  completed_at: string;
  score_percentage: number;
  total_questions: number;
  correct_count: number;
}

export interface ConceptMetricItem {
  concept_id: string;
  concept_name: string;
  mastery_score: number;
  trend_state: 'IMPROVING' | 'STABLE' | 'REQUIRING_ATTENTION' | string;
  total_attempts: number;
  successful_attempts: number;
  consecutive_mistakes: number;
  last_assessed_at?: string;
}

export interface MistakeDistributionItem {
  mistake_type: string;
  count: number;
}

export interface DailyActivityPoint {
  date: string;
  count: number;
}

export interface ActivityEventItem {
  id: string;
  event_type: string;
  project_id?: string;
  project_name?: string;
  created_at: string;
  payload: Record<string, any>;
}

export interface ProjectAnalyticsOverview {
  overall_mastery: number;
  mastery_status: string;
  total_quizzes_completed: number;
  average_quiz_score: number;
  total_questions_answered: number;
  accuracy_rate: number;
  streak_days: number;
  total_materials: number;
  total_chunks: number;
  total_concepts: number;
  ai_queries_count: number;
}

export interface ProjectAnalyticsOut {
  overview: ProjectAnalyticsOverview;
  concept_metrics: ConceptMetricItem[];
  quiz_history: QuizHistoryPoint[];
  mastery_timeline: MasteryTimelinePoint[];
  mistake_distribution: MistakeDistributionItem[];
  daily_activity: DailyActivityPoint[];
  recent_events: ActivityEventItem[];
}

export interface ProjectLeaderboardItem {
  project_id: string;
  project_name: string;
  space_name: string;
  average_mastery: number;
  quizzes_count: number;
  materials_count: number;
}

export interface GlobalAnalyticsOverview {
  total_spaces: number;
  total_projects: number;
  total_materials: number;
  total_quizzes_completed: number;
  platform_average_mastery: number;
  overall_accuracy_rate: number;
  streak_days: number;
  total_ai_interactions: number;
}

export interface GlobalAnalyticsOut {
  overview: GlobalAnalyticsOverview;
  projects_leaderboard: ProjectLeaderboardItem[];
  daily_activity: DailyActivityPoint[];
  recent_events: ActivityEventItem[];
}

export interface AdminUserSummaryOut {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  spaces_count: number;
  projects_count: number;
  quizzes_taken: number;
  average_mastery: number;
  total_ai_tokens: number;
  total_ai_cost: number;
}

export interface AdminUserJourneyDetailOut {
  user: {
    id: string;
    email: string;
    full_name: string;
    role: string;
    created_at: string;
  };
  spaces: {
    id: string;
    name: string;
    description?: string;
    visual_tag: string;
    created_at: string;
  }[];
  projects: {
    id: string;
    space_id: string;
    name: string;
    learning_goal: string;
    created_at: string;
  }[];
  mastery_breakdown: {
    concept_id: string;
    project_id: string;
    concept_name: string;
    importance_score: number;
    mastery_score: number;
    total_attempts: number;
    consecutive_mistakes: number;
    growth_state: string;
    updated_at?: string;
  }[];
  quiz_history: {
    id: string;
    project_id: string;
    title: string;
    score: number;
    status: string;
    created_at: string;
  }[];
  ai_usage: {
    total_requests: number;
    total_tokens: number;
    total_cost_usd: number;
    feature_breakdown: Record<string, number>;
  };
  diagnosed_misconceptions: {
    project_id: string;
    concept?: string;
    diagnosis?: string;
    date?: string;
    text?: string;
  }[];
  recent_activity: {
    id: string;
    project_id?: string;
    event_type: string;
    payload: Record<string, any>;
    created_at: string;
  }[];
}

export interface ActivityEventAdminItem {
  id: string;
  user_id: string;
  user_email?: string;
  project_id?: string;
  project_name?: string;
  event_type: string;
  payload: Record<string, any>;
  created_at: string;
}

export interface ActivityEventAdminResponse {
  items: ActivityEventAdminItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ExamTrapItem {
  misconception_title: string;
  what_student_missed: string;
  exam_trap_warning: string;
  correct_mental_model: string;
  source_page?: number;
  concept_name?: string;
}

export interface CoreFormulaItem {
  name: string;
  formula_or_rule: string;
  plain_explanation: string;
  source_citation: string;
  page_number?: number;
  material_id?: string;
}

export interface HighYieldConceptItem {
  concept_name: string;
  mastery_score: number;
  trend_state: string;
  importance_score: number;
  key_takeaway: string;
  page_number?: number;
}

export interface RapidFireQAItem {
  question: string;
  quick_answer: string;
  key_term: string;
}

export interface CrammingChecklistItem {
  id: string;
  task: string;
  is_critical: boolean;
  estimated_mins: number;
  concept_name?: string;
}

export interface CheatSheetResponse {
  project_id: string;
  project_name: string;
  learning_goal: string;
  exam_readiness_score: number;
  generated_at: string;
  total_concepts_covered: number;
  critical_traps_count: number;
  personalized_traps: ExamTrapItem[];
  core_formulas: CoreFormulaItem[];
  high_yield_concepts: HighYieldConceptItem[];
  rapid_fire_qa: RapidFireQAItem[];
  cramming_checklist: CrammingChecklistItem[];
}


