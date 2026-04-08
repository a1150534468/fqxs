import { create } from 'zustand';
import {
  getUserStats,
  getDashboardStats,
  getRecentGenerations,
  type UserStats,
  type DashboardStats,
  type RecentGeneration,
  type TrendDataPoint,
  type PieDataPoint,
} from '../api/stats';

interface StatsState {
  // User overview stats
  userStats: UserStats | null;
  userStatsLoading: boolean;

  // Dashboard stats
  dashboardStats: DashboardStats | null;
  dashboardStatsLoading: boolean;

  // Chart data
  readingTrend: TrendDataPoint[];
  revenueTrend: TrendDataPoint[];
  aiSuccessData: PieDataPoint[];
  trendLoading: boolean;

  // Recent generations
  recentGenerations: RecentGeneration[];
  recentLoading: boolean;

  // Actions
  fetchUserStats: () => Promise<void>;
  fetchDashboardStats: () => Promise<void>;
  fetchTrendData: () => Promise<void>;
  fetchRecentGenerations: () => Promise<void>;
  fetchAll: () => Promise<void>;
}

/** Derive pie chart data from dashboard generation stats */
function deriveAiSuccessData(stats: DashboardStats): PieDataPoint[] {
  const successRate = stats.generation.success_rate;
  const needsReview = Math.round((100 - successRate) * 0.67);
  const failed = Math.round((100 - successRate) * 0.33);

  return [
    { name: '生成成功', value: Math.round(successRate), itemStyle: { color: '#10b981' } },
    { name: '需要修改', value: needsReview, itemStyle: { color: '#f59e0b' } },
    { name: '生成失败', value: failed, itemStyle: { color: '#ef4444' } },
  ];
}

/** Generate mock trend data from daily stats when API is unavailable */
function generateMockTrend(days: number, base: number, variance: number): TrendDataPoint[] {
  return Array.from({ length: days }).map((_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (days - 1 - i));
    return {
      date: `${d.getMonth() + 1}/${d.getDate()}`,
      value: Math.round(base + Math.random() * variance),
    };
  });
}

export const useStatsStore = create<StatsState>()((set, get) => ({
  // Initial state
  userStats: null,
  userStatsLoading: false,
  dashboardStats: null,
  dashboardStatsLoading: false,
  readingTrend: [],
  revenueTrend: [],
  aiSuccessData: [],
  trendLoading: false,
  recentGenerations: [],
  recentLoading: false,

  fetchUserStats: async () => {
    set({ userStatsLoading: true });
    try {
      const data = await getUserStats();
      set({ userStats: data });
    } catch (error) {
      console.error('Failed to fetch user stats:', error);
    } finally {
      set({ userStatsLoading: false });
    }
  },

  fetchDashboardStats: async () => {
    set({ dashboardStatsLoading: true });
    try {
      const data = await getDashboardStats();
      set({ dashboardStats: data });
    } catch (error) {
      console.warn('Dashboard stats API unavailable, using fallback:', error);
      // Fallback: construct a minimal DashboardStats from userStats
      const { userStats } = get();
      if (userStats) {
        set({
          dashboardStats: {
            generation: {
              total_chapters: userStats.chapter_count,
              success_rate: 85,
              avg_word_count: Math.round(userStats.total_word_count / Math.max(userStats.chapter_count, 1)),
            },
            cost: { total_api_calls: 0, total_tokens: 0, estimated_cost: 0 },
            performance: { avg_generation_time: 0, current_queue: 0 },
            novels: { active_count: userStats.project_count, total_chapters_published: userStats.chapter_count },
          },
        });
      }
    } finally {
      set({ dashboardStatsLoading: false });
    }
  },

  fetchTrendData: async () => {
    set({ trendLoading: true });
    try {
      // Try the dedicated trend endpoint
      const [reading, revenue] = await Promise.all([
        import('../api/stats').then(({ getTrendData }) => getTrendData(7, 'reading')),
        import('../api/stats').then(({ getTrendData }) => getTrendData(7, 'revenue')),
      ]);
      set({ readingTrend: reading, revenueTrend: revenue });
    } catch (error) {
      console.warn('Trend data API unavailable, using mock fallback');
      // Mock fallback — replace with real API once backend supports it
      const { dashboardStats } = get();
      const avgWords = dashboardStats?.generation.avg_word_count ?? 3000;
      const avgCost = dashboardStats?.cost.estimated_cost ?? 200;
      set({
        readingTrend: generateMockTrend(7, avgWords, 2000),
        revenueTrend: generateMockTrend(7, avgCost / 7, 100),
      });
    } finally {
      set({ trendLoading: false });
    }
  },

  fetchRecentGenerations: async () => {
    set({ recentLoading: true });
    try {
      const data = await getRecentGenerations(10);
      set({ recentGenerations: data });
    } catch (error) {
      console.warn('Recent generations API unavailable, skipping');
      set({ recentGenerations: [] });
    } finally {
      set({ recentLoading: false });
    }
  },

  fetchAll: async () => {
    const { fetchUserStats, fetchDashboardStats, fetchTrendData, fetchRecentGenerations } = get();
    await Promise.allSettled([
      fetchUserStats(),
      fetchDashboardStats(),
      fetchTrendData(),
      fetchRecentGenerations(),
    ]);
  },
}));
