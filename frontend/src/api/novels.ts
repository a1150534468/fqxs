import { request } from '../utils/request';

export const getNovels = async (params?: any) => {
  const response = await request.get('/novels/', { params });
  return response.data;
};

export const createNovel = async (data: any) => {
  const response = await request.post('/novels/', data);
  return response.data;
};

export const updateNovel = async (id: number | string, data: any) => {
  const response = await request.patch(`/novels/${id}/`, data);
  return response.data;
};

export const deleteNovel = async (id: number | string) => {
  const response = await request.delete(`/novels/${id}/`);
  return response.data;
};
