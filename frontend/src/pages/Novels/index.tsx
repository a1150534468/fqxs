import { useState, useEffect } from 'react';
import { Table, Button, Tag, Space, Modal, Form, Input, Select, message, Card, Typography, InputNumber } from 'antd';
import { Plus, Edit, Trash2, List } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getNovels, createNovel, updateNovel, deleteNovel } from '../../api/novels';

const { Text } = Typography;
const { TextArea } = Input;

export const Novels = () => {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form] = Form.useForm();

  const STATUS_MAP: Record<string, { color: string, label: string }> = {
    active: { color: 'green', label: '活跃' },
    paused: { color: 'warning', label: '暂停' },
    completed: { color: 'blue', label: '完结' },
    abandoned: { color: 'default', label: '废弃' },
  };

  const fetchData = async (page = pagination.current, pageSize = pagination.pageSize) => {
    try {
      setLoading(true);
      const res = await getNovels({
        page,
        page_size: pageSize,
      });
      if (res.results) {
        setData(res.results);
        setTotal(res.count);
      } else {
        setData(res);
        setTotal(res.length);
      }
      setPagination({ current: page, pageSize });
    } catch (error) {
      console.error('Failed to fetch novels:', error);
      message.error('加载项目列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleTableChange = (newPagination: any) => {
    fetchData(newPagination.current, newPagination.pageSize);
  };

  const handleDelete = async (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除此小说项目吗？（软删除）',
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteNovel(id);
          message.success('删除成功');
          fetchData();
        } catch (error) {
          message.error('删除失败');
        }
      }
    });
  };

  const openCreateModal = () => {
    form.resetFields();
    setEditingId(null);
    setModalOpen(true);
  };

  const openEditModal = (record: any) => {
    form.setFieldsValue({
      title: record.title,
      genre: record.genre,
      status: record.status,
      target_chapters: record.target_chapters,
      synopsis: record.synopsis,
      ai_prompt_template: record.ai_prompt_template,
    });
    setEditingId(record.id);
    setModalOpen(true);
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      if (editingId) {
        await updateNovel(editingId, values);
        message.success('更新成功');
      } else {
        await createNovel(values);
        message.success('创建成功');
      }
      setModalOpen(false);
      fetchData();
    } catch (error: any) {
      if (error.errorFields) return; // Validation error
      message.error(error.response?.data?.detail || '保存失败');
    }
  };

  const columns = [
    {
      title: '书名',
      dataIndex: 'title',
      key: 'title',
      render: (text: string) => <span className="font-medium text-gray-900">{text}</span>,
    },
    {
      title: '分类',
      dataIndex: 'genre',
      key: 'genre',
      width: 120,
      render: (text: string) => <Tag color="blue">{text}</Tag>
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const config = STATUS_MAP[status] || { color: 'default', label: status };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    {
      title: '进度',
      key: 'progress',
      width: 120,
      render: (_: any, record: any) => (
        <Text type="secondary">
          {record.current_chapter} / {record.target_chapters} 章
        </Text>
      ),
    },
    {
      title: '自动生成',
      key: 'auto_generation',
      width: 100,
      render: (_: any, record: any) => (
        <Tag color={record.auto_generation_enabled ? 'green' : 'default'}>
          {record.auto_generation_enabled ? '开启' : '关闭'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString('zh-CN', {
        year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
      }),
    },
    {
      title: '操作',
      key: 'action',
      width: 240,
      render: (_: any, record: any) => (
        <Space size="middle">
          <Button type="text" size="small" className="text-purple-600" icon={<List size={16} />} onClick={(e) => {
            e.stopPropagation();
            navigate(`/novels/${record.id}/chapters`);
          }}>
            章节
          </Button>
          <Button type="text" size="small" className="text-blue-600" icon={<Edit size={16} />} onClick={(e) => {
            e.stopPropagation();
            openEditModal(record);
          }}>
            编辑
          </Button>
          <Button type="text" danger size="small" icon={<Trash2 size={16} />} onClick={(e) => {
            e.stopPropagation();
            handleDelete(record.id);
          }}>
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-semibold text-gray-800">项目管理</h1>
        <Button type="primary" icon={<Plus size={16} />} onClick={openCreateModal}>
          新建项目
        </Button>
      </div>

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
          onRow={(record) => ({
            onClick: () => navigate(`/novels/${record.id}`),
            style: { cursor: 'pointer' }
          })}
        />
      </Card>

      <Modal
        title={editingId ? '编辑项目' : '新建项目'}
        open={modalOpen}
        onOk={handleModalOk}
        onCancel={() => setModalOpen(false)}
        width={600}
        okText="保存"
        cancelText="取消"
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          className="mt-4"
        >
          <Form.Item
            name="title"
            label="书名"
            rules={[{ required: true, message: '请输入书名' }]}
          >
            <Input placeholder="请输入小说书名" />
          </Form.Item>

          <div className="flex gap-4">
            <Form.Item
              name="genre"
              label="分类"
              rules={[{ required: true, message: '请输入或选择分类' }]}
              className="flex-1"
            >
              <Input placeholder="例如：玄幻、都市、言情" />
            </Form.Item>

            <Form.Item
              name="target_chapters"
              label="目标章节数"
              rules={[{ required: true, message: '请输入目标章节数' }]}
              initialValue={100}
              className="w-32"
            >
              <InputNumber min={1} className="w-full" />
            </Form.Item>

            {editingId && (
              <Form.Item
                name="status"
                label="状态"
                rules={[{ required: true }]}
                className="w-32"
              >
                <Select
                  options={[
                    { value: 'active', label: '活跃' },
                    { value: 'paused', label: '暂停' },
                    { value: 'completed', label: '完结' },
                    { value: 'abandoned', label: '废弃' },
                  ]}
                />
              </Form.Item>
            )}
          </div>

          <Form.Item
            name="synopsis"
            label="简介"
          >
            <TextArea rows={3} placeholder="输入小说简介..." />
          </Form.Item>

          <Form.Item
            name="ai_prompt_template"
            label="AI 提示词模板"
            extra="用于生成章节内容的系统 Prompt 模板"
          >
            <TextArea rows={4} placeholder="例如：你是一个经验丰富的小说作者。接下来请根据大纲生成内容..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Novels;
