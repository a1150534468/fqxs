import React, { useEffect, useState } from 'react';
import { Button, Table, Modal, Form, Input, Select, Switch, message, Space, Tag } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ApiOutlined } from '@ant-design/icons';
import { llmProviderApi, type LLMProvider, type LLMProviderCreate } from '../../api/llmProviders';

const LLMProviders: React.FC = () => {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingProvider, setEditingProvider] = useState<LLMProvider | null>(null);
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionTested, setConnectionTested] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchProviders();
  }, []);

  const fetchProviders = async () => {
    setLoading(true);
    try {
      const response = await llmProviderApi.list();
      // Django REST Framework pagination returns {count, next, previous, results}
      const data = (response.data as any).results || response.data;
      setProviders(Array.isArray(data) ? data : []);
    } catch (error) {
      message.error('获取 LLM Provider 列表失败');
      console.error('Failed to fetch providers:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingProvider(null);
    setConnectionTested(false);
    form.resetFields();
    form.setFieldsValue({
      is_active: true,
      priority: 50,
      task_type: 'chapter',
      provider_type: 'openai',
      model: 'gpt-3.5-turbo',
    });
    setModalVisible(true);
  };

  const handleEdit = (provider: LLMProvider) => {
    setEditingProvider(provider);
    setConnectionTested(true); // 编辑时不需要重新测试
    form.setFieldsValue({
      name: provider.name,
      provider_type: provider.provider_type,
      api_url: provider.api_url,
      model: provider.model,
      task_type: provider.task_type,
      is_active: provider.is_active,
      priority: provider.priority,
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个 LLM Provider 吗？',
      onOk: async () => {
        try {
          await llmProviderApi.delete(id);
          message.success('删除成功');
          fetchProviders();
        } catch (error) {
          message.error('删除失败');
        }
      },
    });
  };

  const handleTestConnectionInModal = async () => {
    try {
      // 先验证必填字段
      await form.validateFields(['api_url', 'api_key', 'model']);

      setTestingConnection(true);
      const values = form.getFieldsValue();

      // 直接测试连接，不创建数据库记录
      const response = await llmProviderApi.testConnectionPreview({
        api_url: values.api_url,
        api_key: values.api_key,
        model: values.model,
      });

      if (response.data.status === 'success') {
        message.success('连接测试成功！可以保存配置了');
        setConnectionTested(true);
      } else {
        message.error(response.data.message || '连接测试失败');
      }
    } catch (error: any) {
      message.error(error.response?.data?.message || '连接测试失败，请检查配置');
    } finally {
      setTestingConnection(false);
    }
  };

  const handleTestConnection = async (id: number) => {
    try {
      const response = await llmProviderApi.testConnection(id);
      if (response.data.status === 'success') {
        message.success('连接测试成功');
      } else {
        message.error(response.data.message || '连接测试失败');
      }
    } catch (error: any) {
      message.error(error.response?.data?.message || '连接测试失败');
    }
  };

  const handleSubmit = async () => {
    // 新建时必须先测试连接
    if (!editingProvider && !connectionTested) {
      message.warning('请先测试连接，确保配置正确后再保存');
      return;
    }

    try {
      const values = await form.validateFields();
      if (editingProvider) {
        await llmProviderApi.update(editingProvider.id, values);
        message.success('更新成功');
      } else {
        await llmProviderApi.create(values as LLMProviderCreate);
        message.success('创建成功');
      }
      setModalVisible(false);
      setConnectionTested(false);
      fetchProviders();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '类型',
      dataIndex: 'provider_type',
      key: 'provider_type',
      render: (type: string) => {
        const typeMap: Record<string, { color: string; text: string }> = {
          openai: { color: 'green', text: 'OpenAI' },
          tongyi: { color: 'blue', text: '通义千问' },
          custom: { color: 'purple', text: '自定义' },
        };
        const config = typeMap[type] || { color: 'default', text: type };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: 'API URL',
      dataIndex: 'api_url',
      key: 'api_url',
      ellipsis: true,
    },
    {
      title: 'API Key',
      dataIndex: 'api_key_masked',
      key: 'api_key_masked',
    },
    {
      title: '模型',
      dataIndex: 'model',
      key: 'model',
    },
    {
      title: '任务类型',
      dataIndex: 'task_type',
      key: 'task_type',
      render: (type: string) => {
        const typeMap: Record<string, string> = {
          outline: '大纲生成',
          chapter: '章节生成',
          continue: '内容续写',
        };
        return typeMap[type] || type;
      },
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      sorter: (a: LLMProvider, b: LLMProvider) => b.priority - a.priority,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'success' : 'default'}>{active ? '启用' : '禁用'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: LLMProvider) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<ApiOutlined />}
            onClick={() => handleTestConnection(record.id)}
          >
            测试
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between' }}>
        <h2>LLM Provider 管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          添加 Provider
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={providers}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />

      <Modal
        title={editingProvider ? '编辑 LLM Provider' : '添加 LLM Provider'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          setConnectionTested(false);
        }}
        width={600}
        okText={editingProvider ? '保存' : (connectionTested ? '保存' : '请先测试连接')}
        okButtonProps={{ disabled: !editingProvider && !connectionTested }}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入名称' }]}
          >
            <Input placeholder="例如：OpenAI GPT-3.5" />
          </Form.Item>

          <Form.Item
            name="provider_type"
            label="Provider 类型"
            rules={[{ required: true, message: '请选择类型' }]}
          >
            <Select>
              <Select.Option value="openai">OpenAI</Select.Option>
              <Select.Option value="tongyi">通义千问</Select.Option>
              <Select.Option value="custom">自定义</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="api_url"
            label="API URL"
            rules={[{ required: true, message: '请输入 API URL' }]}
          >
            <Input placeholder="https://api.openai.com/v1" />
          </Form.Item>

          <Form.Item
            name="api_key"
            label="API Key"
            rules={editingProvider ? [] : [{ required: true, message: '请输入 API Key' }]}
          >
            <Input.Password placeholder={editingProvider ? '留空则不修改' : '请输入 API Key'} />
          </Form.Item>

          <Form.Item
            name="model"
            label="模型名称"
            rules={[{ required: true, message: '请输入模型名称' }]}
          >
            <Input placeholder="例如: gpt-3.5-turbo, qwen-turbo, qwen-plus" />
          </Form.Item>

          <Form.Item
            name="task_type"
            label="任务类型"
            rules={[{ required: true, message: '请选择任务类型' }]}
          >
            <Select>
              <Select.Option value="outline">大纲生成</Select.Option>
              <Select.Option value="chapter">章节生成</Select.Option>
              <Select.Option value="continue">内容续写</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="priority"
            label="优先级"
            rules={[{ required: true, message: '请输入优先级' }]}
          >
            <Input type="number" min={0} max={100} placeholder="0-100，数值越大优先级越高" />
          </Form.Item>

          <Form.Item name="is_active" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>

          {!editingProvider && (
            <Form.Item>
              <Button
                type="dashed"
                block
                icon={<ApiOutlined />}
                loading={testingConnection}
                onClick={handleTestConnectionInModal}
              >
                {connectionTested ? '✓ 连接测试成功' : '测试连接'}
              </Button>
              {!connectionTested && (
                <div style={{ marginTop: '8px', color: '#ff4d4f', fontSize: '12px' }}>
                  * 新建 Provider 必须先测试连接成功后才能保存
                </div>
              )}
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  );
};

export default LLMProviders;
