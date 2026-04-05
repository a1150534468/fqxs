import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Form, Input, Button, Card, message, Alert, InputNumber } from 'antd';
import { ArrowLeft, Save, Send } from 'lucide-react';
import MDEditor from '@uiw/react-md-editor';
import { getChapter, createChapter, updateChapter } from '../../api/chapters';

export const ChapterEditor = () => {
  const { projectId, chapterId } = useParams<{ projectId: string; chapterId: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(false);
  
  const isEdit = Boolean(chapterId);

  useEffect(() => {
    if (isEdit && chapterId) {
      loadChapter(chapterId);
    }
  }, [chapterId]);

  const loadChapter = async (id: string) => {
    try {
      setInitialLoading(true);
      const data: any = await getChapter(id);
      form.setFieldsValue({
        title: data.title,
        chapter_number: data.chapter_number,
      });
      setContent(data.final_content || data.raw_content || '');
    } catch (error) {
      message.error('加载章节失败');
      navigate(`/novels/${projectId}/chapters`);
    } finally {
      setInitialLoading(false);
    }
  };

  const getWordCount = (text: string) => {
    // Strip markdown formatting simple attempt and count characters
    const stripped = text.replace(/[#*`_[\]()]/g, '').replace(/\s+/g, '').trim();
    return stripped.length;
  };

  const handleSave = async (publish_status: 'draft' | 'published') => {
    try {
      const values = await form.validateFields();
      if (!content.trim()) {
        message.warning('章节内容不能为空');
        return;
      }

      setLoading(true);
      const payload = {
        ...values,
        project_id: Number(projectId),
        final_content: content,
        publish_status,
      };

      if (isEdit && chapterId) {
        await updateChapter(chapterId, payload);
        message.success('更新成功');
      } else if (projectId) {
        await createChapter(projectId, payload);
        message.success('创建成功');
      }

      navigate(`/novels/${projectId}/chapters`);
    } catch (error: any) {
      if (error.errorFields) return;
      message.error(error.response?.data?.detail || '保存失败');
    } finally {
      setLoading(false);
    }
  };

  if (initialLoading) {
    return <Card loading />;
  }

  const wordCount = getWordCount(content);

  return (
    <div className="space-y-4 max-w-5xl mx-auto">
      <div className="flex items-center gap-4 mb-4">
        <Button icon={<ArrowLeft size={16} />} onClick={() => navigate(`/novels/${projectId}/chapters`)}>
          返回列表
        </Button>
        <h1 className="text-2xl font-semibold text-gray-800 m-0">
          {isEdit ? '编辑章节' : '新建章节'}
        </h1>
      </div>

      <Alert
        message="人工审核规则"
        description={
          <div>
            根据平台规则，AI 生成内容必须人工修改 <strong>&gt;15%</strong>。请务必通读并修改以通过平台审核。
            <br />
            当前字数估算：<strong className="text-blue-600">{wordCount}</strong> 字
          </div>
        }
        type="warning"
        showIcon
        className="mb-4"
      />

      <Card className="shadow-sm border border-gray-100">
        <Form form={form} layout="vertical">
          <div className="flex gap-4">
            <Form.Item
              name="chapter_number"
              label="章节号"
              rules={[{ required: true, message: '请输入章节号' }]}
              className="w-32"
            >
              <InputNumber min={1} className="w-full" />
            </Form.Item>

            <Form.Item
              name="title"
              label="章节标题"
              rules={[{ required: true, message: '请输入章节标题' }]}
              className="flex-1"
            >
              <Input placeholder="例如：第一章 陨落的天才" size="large" />
            </Form.Item>
          </div>

          <Form.Item label="章节内容" required>
            <div data-color-mode="light">
              <MDEditor
                value={content}
                onChange={(val) => setContent(val || '')}
                height={500}
                previewOptions={{
                  disallowedElements: ['style'],
                }}
              />
            </div>
          </Form.Item>

          <div className="flex justify-end gap-3 mt-6">
            <Button 
              size="large" 
              icon={<Save size={18} />} 
              onClick={() => handleSave('draft')}
              loading={loading}
            >
              保存草稿
            </Button>
            <Button 
              type="primary" 
              size="large" 
              icon={<Send size={18} />} 
              onClick={() => handleSave('published')}
              loading={loading}
            >
              发布
            </Button>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default ChapterEditor;
