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
}

export interface Chapter {
  id: number;
  chapter_number: number;
  title?: string;
  word_count?: number;
  status?: string;
  raw_content?: string;
  final_content?: string;
  created_at?: string;
  updated_at?: string;
}

export interface WizardOption {
  title: string;
  preview: string;
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
}
