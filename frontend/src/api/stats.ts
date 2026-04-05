import { request } from '../utils/request';

export interface UserStats {
  project_count: number;
  chapter_count: number;
  total_word_count: number;
  today_chapters?: number; // Backend might not return this yet, mock if undefined
}

export const getUserStats = async (): Promise<UserStats> => {
  const response = await request.get('/users/me/stats/');
  return response.data;
};
