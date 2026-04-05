import { request } from '../utils/request';

export const login = async (data: any) => {
  const response = await request.post('/users/login/', data);
  return response.data;
};

export const getProfile = async () => {
  const response = await request.get('/users/profile/'); // Adjust if needed
  return response.data;
};
