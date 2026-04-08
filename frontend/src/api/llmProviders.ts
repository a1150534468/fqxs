import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

export interface LLMProvider {
  id: number;
  name: string;
  provider_type: string;
  api_url: string;
  api_key_masked: string;
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
  task_type: string;
  is_active: boolean;
  priority: number;
}

export const llmProviderApi = {
  list: () => axios.get<LLMProvider[]>(`${API_BASE_URL}/llm-providers/`),

  create: (data: LLMProviderCreate) =>
    axios.post<LLMProvider>(`${API_BASE_URL}/llm-providers/`, data),

  update: (id: number, data: Partial<LLMProviderCreate>) =>
    axios.patch<LLMProvider>(`${API_BASE_URL}/llm-providers/${id}/`, data),

  delete: (id: number) =>
    axios.delete(`${API_BASE_URL}/llm-providers/${id}/`),

  testConnection: (id: number) =>
    axios.post(`${API_BASE_URL}/llm-providers/${id}/test_connection/`),

  setPriority: (id: number, priority: number) =>
    axios.post(`${API_BASE_URL}/llm-providers/${id}/set_priority/`, { priority }),
};
