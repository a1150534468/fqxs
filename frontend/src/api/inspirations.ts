import { request } from '../utils/request';

export const getInspirations = async (params?: any) => {
  const response = await request.get('/inspirations/', { params });
  return response.data;
};

export const createInspiration = async (data: any) => {
  const response = await request.post('/inspirations/', data);
  return response.data;
};

export const updateInspiration = async (id: number | string, data: any) => {
  const response = await request.patch(`/inspirations/${id}/`, data);
  return response.data;
};

export const deleteInspiration = async (id: number | string) => {
  const response = await request.delete(`/inspirations/${id}/`);
  return response.data;
};

export const generateFromTrends = async () => {
  const response = await request.post('/inspirations/generate-from-trends/');
  return response.data;
};

export const startProject = async (id: number | string) => {
  const response = await request.post(`/inspirations/${id}/start-project/`);
  return response.data;
};

export const generateCustom = async (data: { prompt: string; count: number }) => {
  const response = await request.post('/inspirations/generate-custom/', data);
  return response.data;
};
