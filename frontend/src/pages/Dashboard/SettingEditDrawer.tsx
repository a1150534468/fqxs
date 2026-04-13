import { useCallback, useEffect, useState } from 'react';
import { Button, Drawer, Input, Spin, Tag, message } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import MDEditor from '@uiw/react-md-editor';
import { saveWizardStep } from '../../api/novels';
import { useSettingStream } from '../../hooks/useSettingStream';
import type { NovelSettingRecord } from './types';

const { TextArea } = Input;

interface SettingEditDrawerProps {
  open: boolean;
  onClose: () => void;
  novelId: number | null;
  novelTitle: string;
  setting: NovelSettingRecord | null;
  onSaved: (updated: NovelSettingRecord) => void;
}

const WORLDVIEW_DIMS = [
  { key: 'time_setting', label: '时间设定' },
  { key: 'place_setting', label: '地点设定' },
  { key: 'social_structure', label: '社会结构' },
  { key: 'cultural_background', label: '文化背景' },
  { key: 'tech_level', label: '科技水平' },
  { key: 'power_system', label: '力量体系' },
  { key: 'history', label: '历史背景' },
  { key: 'natural_laws', label: '自然法则' },
];

export const SettingEditDrawer = ({
  open,
  onClose,
  novelId,
  novelTitle,
  setting,
  onSaved,
}: SettingEditDrawerProps) => {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [structured, setStructured] = useState<Record<string, any>>({});
  const [saving, setSaving] = useState(false);

  const { streamingText, isStreaming, generate, stop } = useSettingStream();

  useEffect(() => {
    if (setting) {
      setTitle(setting.title || '');
      setContent(setting.content || '');
      setStructured(setting.structured_data || {});
    } else {
      setTitle('');
      setContent('');
      setStructured({});
    }
  }, [setting]);

  useEffect(() => {
    if (!open) stop();
  }, [open, stop]);

  const handleRegenerate = useCallback(async () => {
    if (!setting) return;
    const res = await generate({
      setting_type: setting.setting_type,
      book_title: novelTitle || '未命名',
      context: content || title,
    });
    if (res) {
      setContent(res.content);
      setStructured(res.structured_data || {});
      if (res.title) setTitle(res.title);
      message.success('重新生成完成');
    }
  }, [setting, novelTitle, content, title, generate]);

  const handleSave = async () => {
    if (!novelId || !setting) return;
    setSaving(true);
    try {
      const saved = await saveWizardStep(novelId, {
        setting_type: setting.setting_type,
        title,
        content,
        structured_data: structured,
      });
      const updated: NovelSettingRecord = {
        setting_type: setting.setting_type,
        title: saved?.title || title,
        content: saved?.content || content,
        structured_data: saved?.structured_data || structured,
      };
      onSaved(updated);
      message.success('保存成功');
      onClose();
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const isWorldview = setting?.setting_type === 'worldview';

  return (
    <Drawer
      title={
        <div className="flex items-center gap-2">
          <span>编辑设定</span>
          {setting && <Tag color="purple">{setting.setting_type}</Tag>}
        </div>
      }
      open={open}
      onClose={onClose}
      width={600}
      extra={
        <div className="flex gap-2">
          <Button
            icon={<ThunderboltOutlined />}
            size="small"
            loading={isStreaming}
            onClick={handleRegenerate}
          >
            重新生成
          </Button>
          <Button type="primary" size="small" loading={saving} onClick={handleSave}>
            保存
          </Button>
        </div>
      }
    >
      {isStreaming && (
        <div className="mb-4 bg-slate-900 text-emerald-100 font-mono text-sm rounded-xl p-3 max-h-48 overflow-auto">
          <Spin size="small" /> <span className="text-xs ml-2">流式生成中...</span>
          <div className="mt-2 whitespace-pre-wrap">{streamingText}</div>
        </div>
      )}

      <div className="space-y-4">
        <div>
          <label className="text-xs text-gray-500">标题</label>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>

        {isWorldview ? (
          <div>
            <label className="text-xs text-gray-500 mb-2 block">八维度结构化数据</label>
            <div className="grid grid-cols-1 gap-3">
              {WORLDVIEW_DIMS.map((d) => (
                <div key={d.key}>
                  <label className="text-xs font-medium text-indigo-600">{d.label}</label>
                  <TextArea
                    autoSize={{ minRows: 2, maxRows: 5 }}
                    value={structured[d.key] || ''}
                    onChange={(e) =>
                      setStructured((prev) => ({ ...prev, [d.key]: e.target.value }))
                    }
                  />
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div>
            <label className="text-xs text-gray-500">Markdown 内容</label>
            <div data-color-mode="light">
              <MDEditor
                value={content}
                onChange={(val) => setContent(val || '')}
                height={320}
              />
            </div>
          </div>
        )}
      </div>
    </Drawer>
  );
};
