export type Mode = 'home' | 'workspace';

export interface Novel {
  id: number;
  title: string;
  genre?: string;
  status?: string;
  synopsis?: string;
  target_chapters?: number;
  current_chapter?: number;
  update_frequency?: number;
  last_update_at?: string;
  auto_generation_enabled?: boolean;
  generation_schedule?: string;
  next_generation_time?: string | null;
}

export interface Chapter {
  id: number;
  chapter_number: number;
  title?: string;
  word_count?: number;
  status?: string;
  raw_content?: string;
  final_content?: string;
  generation_meta?: Record<string, any>;
  context_snapshot?: Record<string, any>;
  summary?: string;
  open_threads?: string[];
  consistency_status?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface NovelSettingRecord {
  setting_type: string;
  title: string;
  content: string;
  structured_data?: Record<string, any>;
  order?: number;
}

export interface KnowledgeGraphPayload {
  nodes: { id: string; name: string; category?: string; symbolSize?: number; info?: Record<string, any> }[];
  links: { source: string; target: string; name?: string; value?: number }[];
  categories?: { name: string }[];
  project_id?: number;
}

export interface ChapterSummaryRecord {
  id: number;
  chapter: number;
  chapter_number: number;
  summary: string;
  key_events: string[];
  open_threads: string[];
}

export interface StorylineRecord {
  id: number;
  name: string;
  storyline_type: string;
  status: string;
  description: string;
  estimated_chapter_start: number;
  estimated_chapter_end: number;
  priority: number;
}

export interface PlotArcPointRecord {
  id: number;
  chapter_number: number;
  point_type: string;
  tension_level: number;
  description: string;
  related_storyline?: number | null;
  related_storyline_name?: string;
}

export interface KnowledgeFactRecord {
  id: number;
  chapter?: number | null;
  chapter_number?: number | null;
  subject: string;
  predicate: string;
  object: string;
  source_excerpt: string;
  confidence: number;
  status: string;
}

export interface ForeshadowItemRecord {
  id: number;
  title: string;
  description: string;
  introduced_in_chapter?: number | null;
  introduced_in_chapter_number?: number | null;
  expected_payoff_chapter: number;
  status: string;
  related_character: string;
}

export interface StyleProfileRecord {
  id: number;
  profile_type: string;
  content: string;
  structured_data: Record<string, any>;
}

export interface ContinuityAlertRecord {
  level: 'info' | 'warning' | 'critical';
  title: string;
  detail: string;
}

export interface MicroBeatRecord {
  index: number;
  label: string;
  focus: string;
  objective: string;
  target_words: number;
}

export interface FocusCardRecord {
  chapter_number: number;
  mission: string;
  conflict: string;
  key_turn: string;
  emotional_note: string;
  ending_hook: string;
  must_keep: string[];
  must_payoff: string[];
  avoid: string[];
}

export interface WorkbenchHighlights {
  focus_chapter_number: number;
  recommended_focus: string;
  active_storyline?: StorylineRecord | null;
  nearest_plot_point?: PlotArcPointRecord | null;
  due_foreshadow_items: ForeshadowItemRecord[];
  continuity_alerts: ContinuityAlertRecord[];
  micro_beats: MicroBeatRecord[];
  focus_card?: FocusCardRecord | null;
  quality_snapshot: {
    consistency_status: string;
    consistency_risks: string[];
    style_risk: string;
    style_tone: string;
  };
}

export interface WorkbenchStats {
  total_words: number;
  finished_chapters: number;
  completion_rate: number;
  average_words: number;
  last_update: string | null;
}

export interface WorkbenchContext {
  project: Novel;
  stats: WorkbenchStats;
  chapters: Chapter[];
  settings: NovelSettingRecord[];
  chapter_summaries: ChapterSummaryRecord[];
  storylines: StorylineRecord[];
  plot_arc_points: PlotArcPointRecord[];
  knowledge_facts: KnowledgeFactRecord[];
  foreshadow_items: ForeshadowItemRecord[];
  style_profiles: StyleProfileRecord[];
  workbench_highlights?: WorkbenchHighlights;
  knowledge_graph: KnowledgeGraphPayload;
}
