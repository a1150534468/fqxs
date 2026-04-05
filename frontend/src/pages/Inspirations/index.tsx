import React, { useState, useEffect } from 'react';
import { Table, Button, Tag, Space, Modal, message, Card, Form, Select, Typography } from 'antd';
import { Eye, CheckCircle, Trash2, ExternalLink } from 'lucide-react';
import { getInspirations, updateInspiration, deleteInspiration } from '../../api/inspirations';

const { Text } = Typography;

export const Inspirations: React.FC = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 });
  const [filters, setFilters] = useState({ is_used: undefined, rank_type: undefined });
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [currentInspiration, setCurrentInspiration] = useState<any>(null);

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

  const handleMarkUsed = async (id: number, isUsed: boolean) => {
    try {
      await updateInspiration(id, { is_used: !isUsed });
      message.success(isUsed ? '已取消标记' : '已标记为使用');
      fetchData();
    } catch (error) {
      message.error('操作失败');
    }
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
      width: 200,
      render: (_: any, record: any) => (
        <Space size="middle">
          <Button type="text" size="small" icon={<Eye size={16} />} onClick={() => showDetail(record)}>
            详情
          </Button>
          <Button 
            type="text" 
            size="small" 
            className={record.is_used ? "text-gray-500" : "text-green-600"}
            icon={<CheckCircle size={16} />} 
            onClick={() => handleMarkUsed(record.id, record.is_used)}
          >
            {record.is_used ? '取消' : '使用'}
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
    </div>
  );
};

export default Inspirations;
