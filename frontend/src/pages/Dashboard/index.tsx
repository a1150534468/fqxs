import { useEffect } from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Spin } from 'antd';
import { BookOutlined, FileTextOutlined, EditOutlined, RiseOutlined } from '@ant-design/icons';
import { useStatsStore } from '../../store/statsStore';
import { LineChart } from '../../components/charts/LineChart';
import { BarChart } from '../../components/charts/BarChart';
import { PieChart } from '../../components/charts/PieChart';

/** Build table columns for recent generation records */
const generateColumns = () => [
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

export const Dashboard = () => {
  const {
    userStats,
    userStatsLoading,
    readingTrend,
    revenueTrend,
    aiSuccessData,
    recentGenerations,
    trendLoading,
    recentLoading,
    fetchUserStats,
    fetchDashboardStats,
    fetchTrendData,
    fetchRecentGenerations,
  } = useStatsStore();

  useEffect(() => {
    // Initial load
    fetchUserStats();
    fetchDashboardStats();
    fetchTrendData();
    fetchRecentGenerations();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchUserStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const columns = generateColumns();

  const statsLoading = userStatsLoading || (readingTrend.length === 0 && trendLoading);

  return (
    <Spin spinning={statsLoading} tip="加载中...">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-800">工作台</h1>
          <p className="text-gray-500 mt-1">欢迎回来，这里是您的创作概览。</p>
        </div>

        {/* Stats Cards — backed by real getUserStats() API */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} lg={6}>
            <Card bordered={false} className="shadow-sm hover:shadow-md transition-shadow">
              <Statistic
                title="总项目数"
                value={userStats?.project_count ?? 0}
                prefix={<BookOutlined className="text-blue-500 mr-2" />}
                loading={userStatsLoading}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card bordered={false} className="shadow-sm hover:shadow-md transition-shadow">
              <Statistic
                title="总章节数"
                value={userStats?.chapter_count ?? 0}
                prefix={<FileTextOutlined className="text-purple-500 mr-2" />}
                loading={userStatsLoading}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card bordered={false} className="shadow-sm hover:shadow-md transition-shadow">
              <Statistic
                title="总字数"
                value={userStats?.total_word_count ?? 0}
                prefix={<EditOutlined className="text-green-500 mr-2" />}
                loading={userStatsLoading}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card bordered={false} className="shadow-sm hover:shadow-md transition-shadow">
              <Statistic
                title="今日新增章节"
                value={userStats?.today_chapters ?? 0}
                prefix={<RiseOutlined className="text-orange-500 mr-2" />}
                loading={userStatsLoading}
              />
            </Card>
          </Col>
        </Row>

        {/* Trend Charts — real data from stats/trend API, mock fallback */}
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card bordered={false} title="近7天阅读量趋势" className="shadow-sm">
              {readingTrend.length > 0 ? (
                <LineChart data={readingTrend} color="#3b82f6" />
              ) : (
                <div className="h-[300px] flex items-center justify-center text-gray-400">暂无数据</div>
              )}
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card bordered={false} title="近7天预估收益 (¥)" className="shadow-sm">
              {revenueTrend.length > 0 ? (
                <BarChart data={revenueTrend.map(d => ({ category: d.date, value: d.value }))} color="#10b981" />
              ) : (
                <div className="h-[300px] flex items-center justify-center text-gray-400">暂无数据</div>
              )}
            </Card>
          </Col>
        </Row>

        {/* AI Stats and Recent Records */}
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={8}>
            <Card bordered={false} title="AI 生成成功率" className="shadow-sm h-full">
              {aiSuccessData.length > 0 ? (
                <PieChart data={aiSuccessData} />
              ) : (
                <div className="h-[300px] flex items-center justify-center text-gray-400">暂无数据</div>
              )}
            </Card>
          </Col>
          <Col xs={24} lg={16}>
            <Card bordered={false} title="最近生成记录" className="shadow-sm h-full">
              {recentLoading ? (
                <div className="h-40 flex items-center justify-center"><Spin /></div>
              ) : recentGenerations.length > 0 ? (
                <Table
                  columns={columns}
                  dataSource={recentGenerations}
                  pagination={false}
                  rowKey="id"
                  size="middle"
                />
              ) : (
                <div className="h-40 flex items-center justify-center text-gray-400">暂无生成记录</div>
              )}
            </Card>
          </Col>
        </Row>
      </div>
    </Spin>
  );
};

export default Dashboard;
