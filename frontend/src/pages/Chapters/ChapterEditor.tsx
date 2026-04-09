import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Form, Input, Button, Card, message, Alert, InputNumber, Modal } from 'antd';
import { ArrowLeft, Save, Send, Upload } from 'lucide-react';
import MDEditor from '@uiw/react-md-editor';
import { getChapter, createChapter, updateChapter, publishChapter } from '../../api/chapters';

export const ChapterEditor = () => {
  const { projectId, chapterId } = useParams<{ projectId: string; chapterId: string }>();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(false);
  const [publishModalOpen, setPublishModalOpen] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [currentChapter, setCurrentChapter] = useState<any>(null);

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
      setCurrentChapter(data);
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

  const handlePublishToTomato = () => {
    if (!isEdit || !currentChapter) {
      message.warning('请先保存章节');
      return;
    }
    if (currentChapter.status !== 'approved') {
      message.warning('只有已审核的章节才能发布');
      return;
    }
    setPublishModalOpen(true);
  };

  const confirmPublish = async () => {
    try {
      setPublishing(true);
      const result = await publishChapter(chapterId!);
      message.success('发布任务已提交');
      setPublishModalOpen(false);

      if (result.publish_url) {
        Modal.success({
          title: '发布成功',
          content: (
            <div>
              <p>章节已成功发布到番茄小说平台</p>
              <a href={result.publish_url} target="_blank" rel="noreferrer" className="text-blue-500">
                查看发布链接
              </a>
            </div>
          ),
        });
      }

      navigate(`/novels/${projectId}/chapters`);
    } catch (error: any) {
      message.error(error.response?.data?.error || '发布失败');
    } finally {
      setPublishing(false);
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
            {isEdit && currentChapter?.status === 'approved' && (
              <Button
                type="primary"
                size="large"
                icon={<Upload size={18} />}
                onClick={handlePublishToTomato}
                className="bg-gradient-to-r from-orange-500 to-red-500 border-0"
              >
                发布到番茄小说
              </Button>
            )}
          </div>
        </Form>
      </Card>

      <Modal
        title="确认发布到番茄小说"
        open={publishModalOpen}
        onOk={confirmPublish}
        onCancel={() => setPublishModalOpen(false)}
        confirmLoading={publishing}
        okText="确认发布"
        cancelText="取消"
      >
        <div className="space-y-4 py-4">
          <Alert
            message="发布前请确认"
            description={
              <ul className="list-disc pl-5 mt-2 space-y-1">
                <li>章节内容已经过人工审核和修改</li>
                <li>内容符合番茄小说平台规范</li>
                <li>发布后将自动提交到平台</li>
                <li>发布过程可能需要几分钟</li>
              </ul>
            }
            type="info"
            showIcon
          />
          {currentChapter && (
            <div className="bg-gray-50 p-4 rounded">
              <div className="space-y-2">
                <div><strong>章节号：</strong>第 {currentChapter.chapter_number} 章</div>
                <div><strong>标题：</strong>{currentChapter.title}</div>
                <div><strong>字数：</strong>{getWordCount(content)} 字</div>
              </div>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
};

export default ChapterEditor;
