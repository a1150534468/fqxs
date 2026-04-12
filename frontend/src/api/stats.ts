import { request } from '../utils/request';

export interface UserStats {
  project_count: number;
  chapter_count: number;
  total_word_count: number;
  today_chapters?: number;
}

export interface DashboardStats {
  generation: {
    total_chapters: number;
    success_rate: number;
    avg_word_count: number;
  };
  cost: {
    total_api_calls: number;
    total_tokens: number;
    estimated_cost: number;
  };
  performance: {
    avg_generation_time: number;
    current_queue: number;
  };
  novels: {
    active_count: number;
    total_chapters_published: number;
  };
}

export interface StatRecord {
  id: number;
  date: string;
  metric_type: string;
  metric_data: Record<string, unknown>;
  created_at?: string;
}

export interface StatsListResponse {
  count: number;
  results: StatRecord[];
  next?: string | null;
  previous?: string | null;
}

export interface TrendDataPoint {
  date: string;
  value: number;
}

export interface PieDataPoint {
  name: string;
  value: number;
  itemStyle?: {
    color: string;
  };
}

export interface RecentGeneration {
  id: number;
  project: string;
  chapter: string;
  status: 'success' | 'warning' | 'error';
  time: string;
  word_count?: number;
}

export interface TaskSummary {
  total: number;
  status_counts: Record<string, number>;
  recent_tasks: {
    id: number;
    task_type: string;
    status: string;
    created_at: string;
    started_at?: string | null;
  }[];
}

export const getUserStats = async (): Promise<UserStats> => {
  const response = await request.get('/users/me/stats/');
  return response.data;
};

/** GET /api/stats/dashboard/ - dashboard overview stats with optional date range */
export const getDashboardStats = async (
  startDate?: string,
  endDate?: string
): Promise<DashboardStats> => {
  const response = await request.get('/stats/dashboard/', {
    params: {
      ...(startDate ? { start_date: startDate } : {}),
      ...(endDate ? { end_date: endDate } : {}),
    },
  });
  return response.data;
};

/** GET /api/stats/ - paginated stats list */
export const getStatsList = async (
  page = 1,
  pageSize = 20,
  metricType?: string
): Promise<StatsListResponse> => {
  const response = await request.get('/stats/', {
    params: {
      page,
      page_size: pageSize,
      ...(metricType ? { metric_type: metricType } : {}),
    },
  });
  return response.data;
};

/**
 * GET /api/stats/trend/ - trend data for charts
 * Returns daily reading/revenue data for a date range.
 * Falls back to computing from stats list if dedicated endpoint not available.
 */
export const getTrendData = async (
  days = 7,
  metricType = 'reading'
): Promise<TrendDataPoint[]> => {
  const response = await request.get('/stats/trend/', {
    params: { days, metric_type: metricType },
  });
  return response.data;
};

/** GET /api/stats/recent-generations/ - recent AI generation records */
export const getRecentGenerations = async (
  limit = 10
): Promise<RecentGeneration[]> => {
  const response = await request.get('/stats/recent-generations/', {
    params: { limit },
  });
  return response.data;
};

/** GET /api/stats/tasks-summary/ - aggregated Celery task queue stats */
export const getTasksSummary = async (): Promise<TaskSummary> => {
  const response = await request.get('/stats/tasks-summary/');
  return response.data;
};
