import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Button, Space, Tag, Progress, Switch, Select, message, Table, Modal, Typography, Spin, Descriptions } from 'antd';
import { ArrowLeft, Zap, Eye, Edit, Send } from 'lucide-react';
import { getNovel, getGenerationStatus, startAutoGeneration, stopAutoGeneration, generateNextChapter } from '../../api/novels';
import { getChapters } from '../../api/chapters';

const { Text, Title } = Typography;

export const ProjectDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<any>(null);
  const [chapters, setChapters] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [chaptersLoading, setChaptersLoading] = useState(false);
  const [autoGenEnabled, setAutoGenEnabled] = useState(false);
  const [frequency, setFrequency] = useState('daily');
  const [nextGenTime, setNextGenTime] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

  const STATUS_MAP: Record<string, { color: string, label: string }> = {
    generating: { color: 'processing', label: '生成中' },
    pending_review: { color: 'warning', label: '待审核' },
    approved: { color: 'success', label: '已审核' },
    published: { color: 'blue', label: '已发布' },
    failed: { color: 'error', label: '失败' },
  };

  const fetchProject = async () => {
    try {
      setLoading(true);
      const data = await getNovel(id!);
      setProject(data);
      setAutoGenEnabled(data.auto_generation_enabled || false);
      setFrequency(data.generation_frequency || 'daily');
    } catch (error) {
      console.error('Failed to fetch project:', error);
      message.error('加载项目详情失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchChapters = async () => {
    try {
      setChaptersLoading(true);
      const res = await getChapters(id!);
      setChapters(res.results || res);
    } catch (error) {
      console.error('Failed to fetch chapters:', error);
    } finally {
      setChaptersLoading(false);
    }
  };

  const fetchGenerationStatus = async () => {
    try {
      const status = await getGenerationStatus(id!);
      setNextGenTime(status.next_generation_time);
    } catch (error) {
      console.error('Failed to fetch generation status:', error);
    }
  };

  useEffect(() => {
    if (id) {
      fetchProject();
      fetchChapters();
      fetchGenerationStatus();
    }
  }, [id]);

  const handleAutoGenToggle = async (checked: boolean) => {
    try {
      if (checked) {
        await startAutoGeneration(id!, { frequency });
        message.success('自动生成已启动');
      } else {
        await stopAutoGeneration(id!);
        message.success('自动生成已停止');
      }
      setAutoGenEnabled(checked);
      fetchGenerationStatus();
    } catch (error: any) {
      message.error(error.response?.data?.error || '操作失败');
    }
  };

  const handleFrequencyChange = async (value: string) => {
    setFrequency(value);
    if (autoGenEnabled) {
      try {
        await startAutoGeneration(id!, { frequency: value });
        message.success('生成频率已更新');
        fetchGenerationStatus();
      } catch (error: any) {
        message.error(error.response?.data?.error || '更新失败');
      }
    }
  };

  const handleGenerateNext = async () => {
    Modal.confirm({
      title: '确认生成',
      content: '确定要生成下一章吗？',
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          setGenerating(true);
          await generateNextChapter(id!);
          message.success('章节生成任务已提交');
          setTimeout(() => {
            fetchChapters();
            fetchProject();
          }, 1000);
        } catch (error: any) {
          message.error(error.response?.data?.error || '生成失败');
        } finally {
          setGenerating(false);
        }
      }
    });
  };

  const chapterColumns = [
    {
      title: '章节号',
      dataIndex: 'chapter_number',
      key: 'chapter_number',
      width: 100,
      render: (num: number) => <Text strong>第 {num} 章</Text>
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const config = STATUS_MAP[status] || { color: 'default', label: status };
        return <Tag color={config.color}>{config.label}</Tag>;
      }
    },
    {
      title: '字数',
      dataIndex: 'word_count',
      key: 'word_count',
      width: 100,
      render: (count: number) => count ? `${count} 字` : '-'
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString('zh-CN', {
        month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
      })
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: any) => (
        <Space size="small">
          <Button
            type="text"
            size="small"
            icon={<Eye size={14} />}
            onClick={() => navigate(`/novels/${id}/chapters/${record.id}/preview`)}
          >
            查看
          </Button>
          <Button
            type="text"
            size="small"
            icon={<Edit size={14} />}
            onClick={() => navigate(`/novels/${id}/chapters/${record.id}/edit`)}
          >
            编辑
          </Button>
          {record.status === 'approved' && (
            <Button
              type="text"
              size="small"
              className="text-green-600"
              icon={<Send size={14} />}
            >
              发布
            </Button>
          )}
        </Space>
      )
    }
  ];

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <Spin size="large" />
      </div>
    );
  }

  if (!project) {
    return <div>项目不存在</div>;
  }

  const progress = project.target_chapters > 0
    ? Math.round((project.current_chapter / project.target_chapters) * 100)
    : 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 mb-4">
        <Button
          icon={<ArrowLeft size={16} />}
          onClick={() => navigate('/novels')}
        >
          返回
        </Button>
        <Title level={2} className="!mb-0">{project.title}</Title>
      </div>

      <Card className="shadow-sm">
        <Descriptions column={3} bordered>
          <Descriptions.Item label="分类">
            <Tag color="blue">{project.genre}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color="green">{project.status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {new Date(project.created_at).toLocaleDateString('zh-CN')}
          </Descriptions.Item>
          <Descriptions.Item label="章节进度" span={3}>
            <div className="flex items-center gap-4">
              <Progress
                percent={progress}
                status={progress === 100 ? 'success' : 'active'}
                className="flex-1"
              />
              <Text type="secondary">
                {project.current_chapter} / {project.target_chapters} 章
              </Text>
            </div>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="自动生成配置" className="shadow-sm">
        <Space direction="vertical" size="large" className="w-full">
          <div className="flex items-center justify-between">
            <div>
              <Text strong>启用自动生成</Text>
              <br />
              <Text type="secondary" className="text-sm">
                开启后系统将按设定频率自动生成章节
              </Text>
            </div>
            <Switch
              checked={autoGenEnabled}
              onChange={handleAutoGenToggle}
              checkedChildren="开启"
              unCheckedChildren="关闭"
            />
          </div>

          <div className="flex items-center gap-4">
            <Text strong>生成频率：</Text>
            <Select
              value={frequency}
              onChange={handleFrequencyChange}
              disabled={!autoGenEnabled}
              style={{ width: 150 }}
              options={[
                { value: 'daily', label: '每天' },
                { value: 'every_2_days', label: '每2天' },
                { value: 'weekly', label: '每周' },
              ]}
            />
          </div>

          {nextGenTime && autoGenEnabled && (
            <div>
              <Text type="secondary">
                下次生成时间：{new Date(nextGenTime).toLocaleString('zh-CN')}
              </Text>
            </div>
          )}

          <div>
            <Button
              type="primary"
              icon={<Zap size={16} />}
              onClick={handleGenerateNext}
              loading={generating}
            >
              立即生成下一章
            </Button>
          </div>
        </Space>
      </Card>

      <Card title="章节列表" className="shadow-sm">
        <Table
          columns={chapterColumns}
          dataSource={chapters}
          rowKey="id"
          loading={chaptersLoading}
          pagination={{ pageSize: 20 }}
        />
      </Card>
    </div>
  );
};

export default ProjectDetail;

