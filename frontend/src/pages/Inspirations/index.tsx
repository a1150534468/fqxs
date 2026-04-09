import React, { useState, useEffect } from 'react';
import { Table, Button, Tag, Space, Modal, message, Card, Form, Select, Typography, Input, InputNumber } from 'antd';
import { Eye, Trash2, ExternalLink, Sparkles, Rocket, Wand2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getInspirations, deleteInspiration, generateFromTrends, startProject, generateCustom } from '../../api/inspirations';

const { Text } = Typography;
const { TextArea } = Input;

export const Inspirations: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [filters, setFilters] = useState({ is_used: undefined, rank_type: undefined });
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [currentInspiration, setCurrentInspiration] = useState<any>(null);
  const [generating, setGenerating] = useState(false);
  const [startingProject, setStartingProject] = useState<number | null>(null);
  const [customModalOpen, setCustomModalOpen] = useState(false);
  const [customGenerating, setCustomGenerating] = useState(false);
  const [customForm] = Form.useForm();

  const fetchData = async (page = pagination.current, pageSize = pagination.pageSize, currentFilters = filters) => {
    try {
      setLoading(true);
      const res = await getInspirations({
        page,
        page_size: pageSize,
        ...currentFilters,
      });
      // Handle standard Django REST framework paginated response
      if (res.results) {
        setData(res.results);
        setTotal(res.count);
      } else {
        setData(res); // if pagination is not standard
        setTotal(res.length);
      }
      setPagination({ current: page, pageSize });
    } catch (error) {
      console.error('Failed to fetch inspirations:', error);
      message.error('加载创意列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(1);
  }, [filters]);

  const handleTableChange = (newPagination: any) => {
    fetchData(newPagination.current, newPagination.pageSize);
  };

  const handleDelete = async (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这条创意吗？此操作不可恢复。',
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteInspiration(id);
          message.success('删除成功');
          fetchData();
        } catch (error) {
          message.error('删除失败');
        }
      }
    });
  };

  const showDetail = (record: any) => {
    setCurrentInspiration(record);
    setDetailModalOpen(true);
  };

  const handleGenerateFromTrends = async () => {
    try {
      setGenerating(true);
      const result = await generateFromTrends();
      message.success(`成功生成 ${result.created_count || 0} 条创意`);
      fetchData(1);
    } catch (error: any) {
      console.error('Failed to generate inspirations:', error);
      message.error(error.response?.data?.error || '生成创意失败');
    } finally {
      setGenerating(false);
    }
  };

  const handleStartProject = async (id: number) => {
    try {
      setStartingProject(id);
      const result = await startProject(id);
      message.success('项目启动成功！正在跳转到章节列表...');

      // Navigate to chapters page after a short delay
      setTimeout(() => {
        navigate(`/novels/${result.project_id}/chapters`);
      }, 1000);
    } catch (error: any) {
      console.error('Failed to start project:', error);
      message.error(error.response?.data?.error || '启动项目失败');
      setStartingProject(null);
    }
  };

  const handleCustomGenerate = async () => {
    try {
      const values = await customForm.validateFields();
      setCustomGenerating(true);
      const result = await generateCustom(values);
      message.success(`成功生成 ${result.created_count || 0} 条创意`);
      setCustomModalOpen(false);
      customForm.resetFields();
      fetchData(1);
    } catch (error: any) {
      if (error.errorFields) return;
      console.error('Failed to generate custom inspirations:', error);
      message.error(error.response?.data?.error || '自定义生成失败');
    } finally {
      setCustomGenerating(false);
    }
  };

  const columns = [
    {
      title: '书名',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: any) => (
        <Space>
          <span className="font-medium">{text}</span>
          {record.source_url && (
            <a href={record.source_url} target="_blank" rel="noreferrer" className="text-gray-400 hover:text-blue-500">
              <ExternalLink size={14} />
            </a>
          )}
        </Space>
      ),
    },
    {
      title: '榜单类型',
      dataIndex: 'rank_type',
      key: 'rank_type',
      width: 120,
    },
    {
      title: '热度',
      dataIndex: 'hot_score',
      key: 'hot_score',
      width: 100,
      sorter: true,
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => (
        <Space size={[0, 4]} wrap>
          {(tags || []).map((tag, i) => (
            <Tag color="blue" key={i}>{tag}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_used',
      key: 'is_used',
      width: 100,
      render: (isUsed: boolean) => (
        <Tag color={isUsed ? 'success' : 'default'}>
          {isUsed ? '已使用' : '未使用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 240,
      render: (_: any, record: any) => (
        <Space size="middle">
          <Button type="text" size="small" icon={<Eye size={16} />} onClick={() => showDetail(record)}>
            详情
          </Button>
          <Button
            type="primary"
            size="small"
            className="bg-gradient-to-r from-purple-500 to-blue-500 border-0"
            icon={<Rocket size={16} />}
            loading={startingProject === record.id}
            onClick={() => handleStartProject(record.id)}
          >
            启动项目
          </Button>
          <Button type="text" danger size="small" icon={<Trash2 size={16} />} onClick={() => handleDelete(record.id)}>
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-semibold text-gray-800">创意库</h1>
        <Space>
          <Button
            type="default"
            icon={<Wand2 size={16} />}
            onClick={() => setCustomModalOpen(true)}
          >
            自定义生成
          </Button>
          <Button
            type="primary"
            icon={<Sparkles size={16} />}
            loading={generating}
            onClick={handleGenerateFromTrends}
            className="bg-gradient-to-r from-green-500 to-teal-500 border-0"
          >
            {generating ? '生成中...' : '生成创意'}
          </Button>
        </Space>
      </div>

      <Card size="small" className="mb-4">
        <Form layout="inline" className="w-full">
          <Form.Item label="状态">
            <Select 
              placeholder="全部" 
              style={{ width: 120 }} 
              allowClear 
              onChange={(val) => setFilters(prev => ({ ...prev, is_used: val }))}
              options={[
                { value: true, label: '已使用' },
                { value: false, label: '未使用' },
              ]}
            />
          </Form.Item>
          {/* Add more filters if rank_types are known */}
        </Form>
      </Card>

      <Card size="small" className="shadow-sm border border-gray-100">
        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: total,
            showSizeChanger: true,
          }}
          onChange={handleTableChange}
          scroll={{ x: 800 }}
        />
      </Card>

      <Modal
        title="创意详情"
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={null}
        width={600}
      >
        {currentInspiration && (
          <div className="space-y-4 pt-4">
            <div>
              <Text type="secondary" className="block mb-1">书名</Text>
              <div className="text-lg font-medium">
                {currentInspiration.title}
                {currentInspiration.source_url && (
                  <a href={currentInspiration.source_url} target="_blank" rel="noreferrer" className="ml-2 text-blue-500 text-sm font-normal">
                    [来源链接]
                  </a>
                )}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Text type="secondary" className="block mb-1">榜单类型</Text>
                <div>{currentInspiration.rank_type || '-'}</div>
              </div>
              <div>
                <Text type="secondary" className="block mb-1">热度</Text>
                <div>{currentInspiration.hot_score}</div>
              </div>
            </div>
            <div>
              <Text type="secondary" className="block mb-1">标签</Text>
              <Space size={[0, 4]} wrap>
                {(currentInspiration.tags || []).map((tag: string, i: number) => (
                  <Tag color="blue" key={i}>{tag}</Tag>
                ))}
              </Space>
            </div>
            <div>
              <Text type="secondary" className="block mb-1">简介</Text>
              <div className="bg-gray-50 p-3 rounded text-gray-700 whitespace-pre-wrap">
                {currentInspiration.synopsis || '无简介'}
              </div>
            </div>
          </div>
        )}
      </Modal>

      <Modal
        title="自定义生成创意"
        open={customModalOpen}
        onOk={handleCustomGenerate}
        onCancel={() => {
          setCustomModalOpen(false);
          customForm.resetFields();
        }}
        confirmLoading={customGenerating}
        okText="生成"
        cancelText="取消"
        width={600}
      >
        <Form
          form={customForm}
          layout="vertical"
          className="mt-4"
        >
          <Form.Item
            name="prompt"
            label="提示词"
            rules={[{ required: true, message: '请输入生成提示词' }]}
            extra="描述你想要生成的创意类型、风格、主题等"
          >
            <TextArea
              rows={6}
              placeholder="例如：生成5个都市言情类小说创意，要求有霸道总裁元素，情节跌宕起伏..."
            />
          </Form.Item>

          <Form.Item
            name="count"
            label="生成数量"
            rules={[{ required: true, message: '请选择生成数量' }]}
            initialValue={3}
          >
            <InputNumber min={1} max={5} className="w-full" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Inspirations;
