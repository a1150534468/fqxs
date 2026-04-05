import { request } from '../utils/request';

export const getChapters = async (projectId: string | number, params?: any) => {
  const response = await request.get('/chapters/', {
    params: {
      project_id: projectId,
      ...params,
    },
  });
  return response.data;
};

export const getChapter = async (id: string | number) => {
  const response = await request.get(`/chapters/${id}/`);
  return response.data;
};

export const createChapter = async (projectId: string | number, data: any) => {
  const response = await request.post('/chapters/', {
    project_id: Number(projectId),
    ...data,
  });
  return response.data;
};

export const updateChapter = async (id: string | number, data: any) => {
  const response = await request.patch(`/chapters/${id}/`, data);
  return response.data;
};

export const deleteChapter = async (id: string | number) => {
  const response = await request.delete(`/chapters/${id}/`);
  return response.data;
};
