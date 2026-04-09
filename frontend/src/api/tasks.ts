import { request } from '../utils/request';

export const getTasks = async (params?: any) => {
  const response = await request.get('/tasks/', { params });
  return response.data;
};

export const getTask = async (id: number | string) => {
  const response = await request.get(`/tasks/${id}/`);
  return response.data;
};
