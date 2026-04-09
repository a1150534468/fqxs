import { request } from '../utils/request';

export interface LLMProvider {
  id: number;
  name: string;
  provider_type: string;
  api_url: string;
  api_key_masked: string;
  model: string;
  task_type: string;
  is_active: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface LLMProviderCreate {
  name: string;
  provider_type: string;
  api_url: string;
  api_key: string;
  model: string;
  task_type: string;
  is_active: boolean;
  priority: number;
}

export const llmProviderApi = {
  list: async () => {
    const response = await request.get<LLMProvider[]>('/llm-providers/');
    return response;
  },

  create: async (data: LLMProviderCreate) => {
    const response = await request.post<LLMProvider>('/llm-providers/', data);
    return response;
  },

  update: async (id: number, data: Partial<LLMProviderCreate>) => {
    const response = await request.patch<LLMProvider>(`/llm-providers/${id}/`, data);
    return response;
  },

  delete: async (id: number) => {
    const response = await request.delete(`/llm-providers/${id}/`);
    return response;
  },

  testConnection: async (id: number) => {
    const response = await request.post(`/llm-providers/${id}/test_connection/`);
    return response;
  },

  testConnectionPreview: async (data: { api_url: string; api_key: string; model: string }) => {
    const response = await request.post('/llm-providers/test_connection_preview/', data);
    return response;
  },

  setPriority: async (id: number, priority: number) => {
    const response = await request.post(`/llm-providers/${id}/set_priority/`, { priority });
    return response;
  },
};
