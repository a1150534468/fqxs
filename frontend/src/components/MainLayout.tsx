import React, { useState } from 'react';
import { Layout, Menu, Button, Dropdown, theme } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { 
  LayoutDashboard, 
  Lightbulb, 
  BookOpen, 
  Menu as MenuIcon, 
  LogOut, 
  User as UserIcon 
} from 'lucide-react';

const { Header, Sider, Content } = Layout;

export const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const { token } = theme.useToken();
  const navigate = useNavigate();
  const location = useLocation();
  const { user, clearAuth } = useAuthStore();

  const handleLogout = () => {
    clearAuth();
    navigate('/login');
  };

  const menuItems = [
    {
      key: '/',
      icon: <LayoutDashboard size={18} />,
      label: 'Dashboard',
    },
    {
      key: '/inspirations',
      icon: <Lightbulb size={18} />,
      label: '创意库',
    },
    {
      key: '/novels',
      icon: <BookOpen size={18} />,
      label: '项目管理',
    },
  ];

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserIcon size={16} />,
      label: user?.username || 'Profile',
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogOut size={16} />,
      label: '退出登录',
      onClick: handleLogout,
    },
  ];

  return (
    <Layout className="min-h-screen">
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed}
        breakpoint="lg"
        onBreakpoint={(broken) => {
          setCollapsed(broken);
        }}
        theme="light"
        className="border-r border-gray-200"
      >
        <div className="h-16 flex items-center justify-center border-b border-gray-200">
          <span className="text-xl font-bold text-blue-600 truncate px-4">
            {collapsed ? 'FQ' : '番茄小说辅助'}
          </span>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          className="border-r-0 py-4"
        />
      </Sider>
      <Layout>
        <Header 
          style={{ padding: 0, background: token.colorBgContainer }}
          className="flex items-center justify-between px-4 border-b border-gray-200"
        >
          <Button
            type="text"
            icon={<MenuIcon size={20} />}
            onClick={() => setCollapsed(!collapsed)}
            className="flex items-center justify-center w-10 h-10"
          />
          <div className="flex items-center gap-4">
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Button type="text" className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-semibold">
                  {user?.username?.charAt(0).toUpperCase() || 'U'}
                </div>
                <span className="hidden sm:inline">{user?.username}</span>
              </Button>
            </Dropdown>
          </div>
        </Header>
        <Content className="m-4 md:m-6 p-4 md:p-6 bg-white rounded-lg shadow-sm overflow-auto">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};
