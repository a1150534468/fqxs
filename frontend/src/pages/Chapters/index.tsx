import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Table, Button, Space, Tag, Input, Select, Card, message, Modal, Alert } from 'antd';
import { Plus, Edit, Trash2, ArrowLeft, Eye } from 'lucide-react';
import { getChapters, deleteChapter } from '../../api/chapters';

export const Chapters = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [filters, setFilters] = useState({ search: '', publish_status: undefined });

  const STATUS_MAP: Record<string, { color: string, label: string }> = {
    draft: { color: 'default', label: '草稿' },
    published: { color: 'success', label: '已发布' },
    failed: { color: 'error', label: '失败' },
  };

  const fetchData = async (page = pagination.current, pageSize = pagination.pageSize, currentFilters = filters) => {
    if (!projectId) return;
    try {
      setLoading(true);
      const res: any = await getChapters(projectId, {
        page,
        page_size: pageSize,
        ...currentFilters,
      });
      setData(res.results || []);
      setTotal(res.count || 0);
      setPagination({ current: page, pageSize });
    } catch (error) {
      console.error('Failed to fetch chapters:', error);
      message.error('获取章节列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(1);
  }, [projectId, filters]);

  const handleTableChange = (newPagination: any) => {
    fetchData(newPagination.current, newPagination.pageSize);
  };

  const handleDelete = async (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除此章节吗？此操作不可恢复。',
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteChapter(id);
          message.success('删除成功');
          fetchData();
        } catch (error) {
          message.error('删除失败');
        }
      }
    });
  };

  const columns = [
    {
      title: '章节号',
      dataIndex: 'chapter_number',
      key: 'chapter_number',
      width: 80,
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (text: string) => <span className="font-medium text-gray-800">{text}</span>,
    },
    {
      title: '状态',
      dataIndex: 'publish_status',
      key: 'publish_status',
      width: 100,
      render: (status: string) => {
        const config = STATUS_MAP[status] || { color: 'default', label: status };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '字数',
      dataIndex: 'word_count',
      key: 'word_count',
      width: 100,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (date: string) => new Date(date).toLocaleString('zh-CN', {
        month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
      }),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: any) => (
        <Space size="small">
          <Button type="text" size="small" icon={<Eye size={16} />} onClick={() => navigate(`/novels/${projectId}/chapters/${record.id}/preview`)}>
            预览
          </Button>
          <Button type="text" size="small" className="text-blue-600" icon={<Edit size={16} />} onClick={() => navigate(`/novels/${projectId}/chapters/${record.id}/edit`)}>
            编辑
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
      <div className="flex items-center gap-4 mb-4">
        <Button icon={<ArrowLeft size={16} />} onClick={() => navigate('/novels')}>
          返回项目列表
        </Button>
        <h1 className="text-2xl font-semibold text-gray-800 m-0">章节管理</h1>
        <div className="flex-1" />
        <Button type="primary" icon={<Plus size={16} />} onClick={() => navigate(`/novels/${projectId}/chapters/create`)}>
          新建章节
        </Button>
      </div>

      <Card size="small" className="mb-4">
        <div className="flex gap-4">
          <Input.Search
            placeholder="搜索章节标题..."
            allowClear
            onSearch={(val) => setFilters(prev => ({ ...prev, search: val }))}
            style={{ width: 300 }}
          />
          <Select
            placeholder="按状态筛选"
            allowClear
            style={{ width: 120 }}
            onChange={(val) => setFilters(prev => ({ ...prev, publish_status: val }))}
            options={[
              { value: 'draft', label: '草稿' },
              { value: 'published', label: '已发布' },
              { value: 'failed', label: '失败' },
            ]}
          />
        </div>
      </Card>

      <Alert
        message="人工审核提示"
        description="根据平台规则，AI 生成内容必须人工修改 >15%。发布前请务必认真检查修改。"
        type="warning"
        showIcon
        className="mb-4"
      />

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
    </div>
  );
};

export default Chapters;
