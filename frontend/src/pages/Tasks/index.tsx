import { useState, useEffect } from 'react';
import { Table, Card, Tag, Button, Space, Select, Modal, Typography, message } from 'antd';
import { RefreshCw, Eye } from 'lucide-react';
import { getTasks, getTask } from '../../api/tasks';

const { Text } = Typography;

export const Tasks = () => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20 });
  const [filters, setFilters] = useState({ task_type: undefined, status: undefined });
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [currentTask, setCurrentTask] = useState<any>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const STATUS_MAP: Record<string, { color: string, label: string }> = {
    pending: { color: 'default', label: '待处理' },
    running: { color: 'processing', label: '运行中' },
    success: { color: 'success', label: '成功' },
    failed: { color: 'error', label: '失败' },
  };

  const TASK_TYPE_MAP: Record<string, string> = {
    generate_chapter: '生成章节',
    publish_chapter: '发布章节',
    collect_inspiration: '采集创意',
    generate_inspiration: '生成创意',
  };

  const fetchData = async (page = pagination.current, pageSize = pagination.pageSize, currentFilters = filters) => {
    try {
      setLoading(true);
      const res = await getTasks({
        page,
        page_size: pageSize,
        ...currentFilters,
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
      console.error('Failed to fetch tasks:', error);
      message.error('加载任务列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(1);
  }, [filters]);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchData(pagination.current, pagination.pageSize, filters);
    }, 5000);

    return () => clearInterval(interval);
  }, [autoRefresh, pagination.current, pagination.pageSize, filters]);

  const handleTableChange = (newPagination: any) => {
    fetchData(newPagination.current, newPagination.pageSize);
  };

  const showDetail = async (record: any) => {
    try {
      const task = await getTask(record.id);
      setCurrentTask(task);
      setDetailModalOpen(true);
    } catch (error) {
      message.error('加载任务详情失败');
    }
  };

  const columns = [
    {
      title: '任务ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '任务类型',
      dataIndex: 'task_type',
      key: 'task_type',
      width: 120,
      render: (type: string) => TASK_TYPE_MAP[type] || type,
    },
    {
      title: '关联对象',
      key: 'related',
      width: 200,
      render: (_: any, record: any) => {
        if (record.chapter_id) {
          return <Text type="secondary">章节 #{record.chapter_id}</Text>;
        }
        if (record.project_id) {
          return <Text type="secondary">项目 #{record.project_id}</Text>;
        }
        return '-';
      }
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const config = STATUS_MAP[status] || { color: 'default', label: status };
        return <Tag color={config.color}>{config.label}</Tag>;
      }
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => new Date(date).toLocaleString('zh-CN', {
        month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit'
      })
    },
    {
      title: '完成时间',
      dataIndex: 'completed_at',
      key: 'completed_at',
      width: 180,
      render: (date: string) => date ? new Date(date).toLocaleString('zh-CN', {
        month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit'
      }) : '-'
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: any) => (
        <Button
          type="text"
          size="small"
          icon={<Eye size={14} />}
          onClick={() => showDetail(record)}
        >
          详情
        </Button>
      )
    }
  ];

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-semibold text-gray-800">任务监控</h1>
        <Space>
          <Button
            icon={<RefreshCw size={16} />}
            onClick={() => fetchData()}
            loading={loading}
          >
            刷新
          </Button>
          <Select
            value={autoRefresh}
            onChange={setAutoRefresh}
            style={{ width: 120 }}
            options={[
              { value: true, label: '自动刷新' },
              { value: false, label: '手动刷新' },
            ]}
          />
        </Space>
      </div>

      <Card size="small" className="mb-4">
        <Space size="large">
          <Space>
            <Text>任务类型：</Text>
            <Select
              placeholder="全部"
              style={{ width: 150 }}
              allowClear
              onChange={(val) => setFilters(prev => ({ ...prev, task_type: val }))}
              options={Object.entries(TASK_TYPE_MAP).map(([value, label]) => ({ value, label }))}
            />
          </Space>
          <Space>
            <Text>状态：</Text>
            <Select
              placeholder="全部"
              style={{ width: 120 }}
              allowClear
              onChange={(val) => setFilters(prev => ({ ...prev, status: val }))}
              options={[
                { value: 'pending', label: '待处理' },
                { value: 'running', label: '运行中' },
                { value: 'success', label: '成功' },
                { value: 'failed', label: '失败' },
              ]}
            />
          </Space>
        </Space>
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
          scroll={{ x: 1000 }}
        />
      </Card>

      <Modal
        title="任务详情"
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={null}
        width={700}
      >
        {currentTask && (
          <div className="space-y-4 pt-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Text type="secondary" className="block mb-1">任务ID</Text>
                <div>{currentTask.id}</div>
              </div>
              <div>
                <Text type="secondary" className="block mb-1">任务类型</Text>
                <div>{TASK_TYPE_MAP[currentTask.task_type] || currentTask.task_type}</div>
              </div>
              <div>
                <Text type="secondary" className="block mb-1">状态</Text>
                <Tag color={STATUS_MAP[currentTask.status]?.color || 'default'}>
                  {STATUS_MAP[currentTask.status]?.label || currentTask.status}
                </Tag>
              </div>
              <div>
                <Text type="secondary" className="block mb-1">创建时间</Text>
                <div>{new Date(currentTask.created_at).toLocaleString('zh-CN')}</div>
              </div>
            </div>

            {currentTask.params && (
              <div>
                <Text type="secondary" className="block mb-1">任务参数</Text>
                <pre className="bg-gray-50 p-3 rounded text-sm overflow-auto">
                  {JSON.stringify(currentTask.params, null, 2)}
                </pre>
              </div>
            )}

            {currentTask.result && (
              <div>
                <Text type="secondary" className="block mb-1">执行结果</Text>
                <pre className="bg-gray-50 p-3 rounded text-sm overflow-auto">
                  {JSON.stringify(currentTask.result, null, 2)}
                </pre>
              </div>
            )}

            {currentTask.error_message && (
              <div>
                <Text type="secondary" className="block mb-1">错误信息</Text>
                <div className="bg-red-50 p-3 rounded text-red-700">
                  {currentTask.error_message}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Tasks;
