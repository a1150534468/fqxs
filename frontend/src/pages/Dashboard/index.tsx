import { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Table, message, Tag } from 'antd';
import { BookOutlined, FileTextOutlined, EditOutlined, RiseOutlined } from '@ant-design/icons';
import { getUserStats } from '../../api/stats';
import type { UserStats } from '../../api/stats';
import { LineChart } from '../../components/charts/LineChart';
import { BarChart } from '../../components/charts/BarChart';
import { PieChart } from '../../components/charts/PieChart';

export const Dashboard = () => {
  const [stats, setStats] = useState<UserStats>({
    project_count: 0,
    chapter_count: 0,
    total_word_count: 0,
    today_chapters: 0,
  });
  const [loading, setLoading] = useState(false);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const data = await getUserStats();
      setStats({
        ...data,
        today_chapters: data.today_chapters || Math.floor(Math.random() * 10), // Mock if missing
      });
    } catch (error) {
      console.error('Failed to fetch stats:', error);
      message.error('获取统计数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  // Mock data for charts
  const readingTrendData = Array.from({ length: 7 }).map((_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    return {
      date: `${d.getMonth() + 1}/${d.getDate()}`,
      value: Math.floor(Math.random() * 5000) + 1000,
    };
  });

  const revenueTrendData = Array.from({ length: 7 }).map((_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    return {
      category: `${d.getMonth() + 1}/${d.getDate()}`,
      value: Math.floor(Math.random() * 500) + 50,
    };
  });

  const aiSuccessData = [
    { name: '生成成功', value: 85, itemStyle: { color: '#10b981' } },
    { name: '需要修改', value: 10, itemStyle: { color: '#f59e0b' } },
    { name: '生成失败', value: 5, itemStyle: { color: '#ef4444' } },
  ];

  // Mock recent generations
  const recentGenerations = [
    { id: 1, project: '《剑道独尊》', chapter: '第128章 突破', status: 'success', time: '10分钟前' },
    { id: 2, project: '《都市医神》', chapter: '第56章 震撼全场', status: 'success', time: '1小时前' },
    { id: 3, project: '《深空黎明》', chapter: '第12章 星际海盗', status: 'warning', time: '2小时前' },
    { id: 4, project: '《剑道独尊》', chapter: '第127章 强敌来袭', status: 'success', time: '3小时前' },
    { id: 5, project: '《九龙夺嫡》', chapter: '第8章 暗流涌动', status: 'error', time: '5小时前' },
  ];

  const columns = [
    {
      title: '项目',
      dataIndex: 'project',
      key: 'project',
      render: (text: string) => <span className="font-medium">{text}</span>,
    },
    {
      title: '章节',
      dataIndex: 'chapter',
      key: 'chapter',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        let color = 'success';
        let text = '成功';
        if (status === 'warning') { color = 'warning'; text = '待修改'; }
        if (status === 'error') { color = 'error'; text = '失败'; }
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '时间',
      dataIndex: 'time',
      key: 'time',
      align: 'right' as const,
      className: 'text-gray-400',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-800">工作台</h1>
        <p className="text-gray-500 mt-1">欢迎回来，这里是您的创作概览。</p>
      </div>

      {/* Stats Cards */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} className="shadow-sm hover:shadow-md transition-shadow">
            <Statistic
              title="总项目数"
              value={stats.project_count}
              prefix={<BookOutlined className="text-blue-500 mr-2" />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} className="shadow-sm hover:shadow-md transition-shadow">
            <Statistic
              title="总章节数"
              value={stats.chapter_count}
              prefix={<FileTextOutlined className="text-purple-500 mr-2" />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} className="shadow-sm hover:shadow-md transition-shadow">
            <Statistic
              title="总字数"
              value={stats.total_word_count}
              prefix={<EditOutlined className="text-green-500 mr-2" />}
              loading={loading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bordered={false} className="shadow-sm hover:shadow-md transition-shadow">
            <Statistic
              title="今日新增章节"
              value={stats.today_chapters}
              prefix={<RiseOutlined className="text-orange-500 mr-2" />}
              loading={loading}
            />
          </Card>
        </Col>
      </Row>

      {/* Trend Charts */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card bordered={false} title="近7天阅读量趋势" className="shadow-sm">
            <LineChart data={readingTrendData} color="#3b82f6" />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card bordered={false} title="近7天预估收益 (¥)" className="shadow-sm">
            <BarChart data={revenueTrendData} color="#10b981" />
          </Card>
        </Col>
      </Row>

      {/* AI Stats and Recent Records */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card bordered={false} title="AI 生成成功率" className="shadow-sm h-full">
            <PieChart data={aiSuccessData} />
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Card bordered={false} title="最近生成记录" className="shadow-sm h-full">
            <Table
              columns={columns}
              dataSource={recentGenerations}
              pagination={false}
              rowKey="id"
              size="middle"
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
