import React, { useState } from 'react';
import { Form, Input, Button, Card, message } from 'antd';
import { User, Lock } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { login } from '../../api/auth';
import { useAuthStore } from '../../store/authStore';

export const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const setAuth = useAuthStore((state) => state.setAuth);

  const onFinish = async (values: any) => {
    try {
      setLoading(true);
      const data = await login(values);
      setAuth(data.access, data.refresh, data.user);
      
      message.success('登录成功');
      
      const from = (location.state as any)?.from?.pathname || '/';
      navigate(from, { replace: true });
    } catch (error: any) {
      console.error('Login failed:', error);
      message.error(error.response?.data?.detail || '登录失败，请检查用户名和密码');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md shadow-lg border-0 rounded-xl">
        <div className="mb-8 text-center">
          <h2 className="text-3xl font-extrabold text-gray-900 mb-2">番茄小说辅助</h2>
          <p className="text-gray-500">登录您的账号以继续</p>
        </div>
        
        <Form
          name="login"
          onFinish={onFinish}
          layout="vertical"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名！' }]}
          >
            <Input 
              prefix={<User size={18} className="text-gray-400" />} 
              placeholder="用户名" 
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码！' }]}
          >
            <Input.Password 
              prefix={<Lock size={18} className="text-gray-400" />} 
              placeholder="密码" 
            />
          </Form.Item>

          <Form.Item className="mb-0 mt-6">
            <Button 
              type="primary" 
              htmlType="submit" 
              className="w-full h-11 text-base font-medium"
              loading={loading}
            >
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default Login;
