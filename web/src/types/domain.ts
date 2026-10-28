export type Answer = 'yes' | 'no' | 'unanswered';
export type Category = 'automatable' | 'ai_accelerated' | 'human_critical' | 'emerging_value' | 'unresolved';
export interface Task { id: string; task_description: string; hours_per_week: number | ''; frequency: string | null; tools_used: string[]; skills_used: string[]; involves_people: Answer; physical_presence_required: Answer; decision_authority: number | null; notes: string | null; }
export interface Evidence { synthetic: boolean; matched_reference_tasks: { name: string; similarity: number; source_name: string; release_id: string; source_url: string | null }[]; raw_signals: string[]; transformed_signals: string[]; weights_and_contributions: string[]; missing_evidence: string[]; fallback: string | null; scoring_config_version: string; uncertainty_reasons: string[]; }
export interface TaskResult { task_id: string; category: Category; explanation: string; indicators: { automation: number; acceleration: number }; evidence: Evidence; }
export interface Analysis { id: string; demonstration: boolean; snapshot: Task[]; results: TaskResult[]; version: string; created_at: string; }
export interface Scenario { adoption: 'low'|'medium'|'high'; horizon: 1|3|5; original: number; freed: number; remaining: number; unresolved: number; assumptions_version: string; }
export interface PlanAction { id: string; title: string; explanation: string; hours_per_week: number; task_refs: string[]; evidence_refs: string[]; }
export interface DevelopmentPlan { demonstration: boolean; learning_budget: number; phases: { label: string; actions: PlanAction[] }[]; status: 'success'|'outdated'; }
export const blankTask = (): Task => ({ id: crypto.randomUUID(), task_description:'', hours_per_week:'', frequency:null, tools_used:[], skills_used:[], involves_people:'unanswered', physical_presence_required:'unanswered', decision_authority:null, notes:'' });
