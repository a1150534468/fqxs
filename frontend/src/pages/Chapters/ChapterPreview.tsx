import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Button, Descriptions, Tag, message } from 'antd';
import { ArrowLeft, Edit } from 'lucide-react';
import MDEditor from '@uiw/react-md-editor';
import { getChapter } from '../../api/chapters';

export const ChapterPreview = () => {
  const { projectId, chapterId } = useParams<{ projectId: string; chapterId: string }>();
  const navigate = useNavigate();
  const [chapter, setChapter] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (chapterId) {
      loadChapter(chapterId);
    }
  }, [chapterId]);

  const loadChapter = async (id: string) => {
    try {
      setLoading(true);
      const data = await getChapter(id);
      setChapter(data);
    } catch (error) {
      message.error('加载章节详情失败');
      navigate(`/novels/${projectId}/chapters`);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <Card loading />;
  if (!chapter) return null;

  return (
    <div className="space-y-4 max-w-5xl mx-auto">
      <div className="flex items-center gap-4 mb-4">
        <Button icon={<ArrowLeft size={16} />} onClick={() => navigate(`/novels/${projectId}/chapters`)}>
          返回列表
        </Button>
        <h1 className="text-2xl font-semibold text-gray-800 m-0">章节预览</h1>
        <div className="flex-1" />
        <Button type="primary" icon={<Edit size={16} />} onClick={() => navigate(`/novels/${projectId}/chapters/${chapterId}/edit`)}>
          编辑内容
        </Button>
      </div>

      <Card size="small" className="shadow-sm border border-gray-100">
        <Descriptions column={{ xs: 1, sm: 2, md: 4 }} className="mt-2">
          <Descriptions.Item label="章节号">第 {chapter.chapter_number} 章</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={chapter.publish_status === 'published' ? 'success' : chapter.publish_status === 'draft' ? 'default' : 'error'}>
              {chapter.publish_status === 'published' ? '已发布' : chapter.publish_status === 'draft' ? '草稿' : '失败'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="字数">{chapter.word_count}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{new Date(chapter.created_at).toLocaleString()}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card className="shadow-sm border border-gray-100 min-h-[600px]" bodyStyle={{ padding: '2rem' }}>
        <h1 className="text-3xl font-bold text-center mb-8">{chapter.title}</h1>
        <div data-color-mode="light">
          <MDEditor.Markdown source={chapter.final_content || chapter.raw_content || '*暂无内容*'} />
        </div>
      </Card>
    </div>
  );
};

export default ChapterPreview;
