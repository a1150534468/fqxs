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

export const getNovel = async (id: number | string) => {
  const response = await request.get(`/novels/${id}/`);
  return response.data;
};

export const getGenerationStatus = async (id: number | string) => {
  const response = await request.get(`/novels/${id}/generation-status/`);
  return response.data;
};

export const getWorkbenchContext = async (projectId: number | string) => {
  const response = await request.get(`/workbench/${projectId}/context/`);
  return response.data;
};

export const startAutoGeneration = async (id: number | string, data: { frequency: string }) => {
  const response = await request.post(`/novels/${id}/start-auto-generation/`, data);
  return response.data;
};

export const stopAutoGeneration = async (id: number | string) => {
  const response = await request.post(`/novels/${id}/stop-auto-generation/`);
  return response.data;
};

export const generateNextChapter = async (id: number | string) => {
  const response = await request.post(`/novels/${id}/generate-next-chapter/`);
  return response.data;
};

export const generateSetting = async (id: number | string, data: { setting_type: string; context: string }) => {
  const response = await request.post(`/novels/${id}/generate-setting/`, data);
  return response.data;
};

export const saveWizardStep = async (id: number | string, data: { setting_type: string; title: string; content: string; structured_data?: any }) => {
  const response = await request.post(`/novels/${id}/wizard-step/`, data);
  return response.data;
};

export const getNovelSettings = async (id: number | string) => {
  const response = await request.get(`/novels/${id}/settings/`);
  return response.data;
};

export const getKnowledgeGraph = async (id: number | string) => {
  const response = await request.get(`/novels/${id}/knowledge-graph/`);
  return response.data;
};

export const completeWizard = async (id: number | string) => {
  const response = await request.post(`/novels/${id}/complete-wizard/`);
  return response.data;
};

// ------------------------------------------------------------------ //
// Draft (12-step wizard pre-project) APIs
// ------------------------------------------------------------------ //

export interface DraftPayload {
  inspiration: string;
  title?: string;
  genre?: string;
  style_preference?: string;
}

export interface DraftTitleGenerationPayload {
  count?: number;
}

export interface DraftTitleGenerationResponse {
  titles: string[];
  style_preference: string;
}

export const createDraft = async (data: DraftPayload) => {
  const response = await request.post('/drafts/', data);
  return response.data;
};

export const generateDraftTitles = async (
  id: number | string,
  data: DraftTitleGenerationPayload = {},
): Promise<DraftTitleGenerationResponse> => {
  const response = await request.post(`/drafts/${id}/generate-titles/`, data);
  return response.data;
};

export const getDrafts = async () => {
  const response = await request.get('/drafts/');
  return response.data;
};

export const getDraft = async (id: number | string) => {
  const response = await request.get(`/drafts/${id}/`);
  return response.data;
};

export const updateDraft = async (id: number | string, data: any) => {
  const response = await request.patch(`/drafts/${id}/`, data);
  return response.data;
};

export const deleteDraft = async (id: number | string) => {
  const response = await request.delete(`/drafts/${id}/`);
  return response.data;
};

export const saveDraftStep = async (
  id: number | string,
  data: { setting_type: string; title: string; content: string; structured_data?: any },
) => {
  const response = await request.post(`/drafts/${id}/save-step/`, data);
  return response.data;
};

export const getDraftSettings = async (id: number | string) => {
  const response = await request.get(`/drafts/${id}/settings/`);
  return response.data;
};

export const completeDraft = async (id: number | string) => {
  const response = await request.post(`/drafts/${id}/complete/`);
  return response.data;
};
