import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button, Empty, Input, Modal, Spin, Steps, Tag, Tooltip, Progress, message } from 'antd';
import { ThunderboltOutlined, PauseOutlined, PlayCircleOutlined } from '@ant-design/icons';
import MDEditor from '@uiw/react-md-editor';
import ReactECharts from 'echarts-for-react';
import { wizardSteps, WIZARD_STEP_TYPES, STEP_PRESETS } from './constants';
import {
  getDraftSettings,
  saveDraftStep,
  completeDraft,
} from '../../api/novels';
import { useSettingStream } from '../../hooks/useSettingStream';
import type { NovelSettingRecord } from './types';

const { TextArea } = Input;

interface NewBookWizardProps {
  open: boolean;
  onClose: () => void;
  draftId: number | null;
  pendingTitle: string;
  onFinished: (newProjectId?: number) => void;
}

const pickArray = (response: any): any[] => {
  if (!response) return [];
  if (Array.isArray(response.results)) return response.results;
  if (Array.isArray(response)) return response;
  return [];
};

const FINAL_STEP_INDEX = wizardSteps.length - 1; // 11 (进入工作台)

export const NewBookWizard = ({
  open,
  onClose,
  draftId,
  pendingTitle,
  onFinished,
}: NewBookWizardProps) => {
  const [step, setStep] = useState(0);
  const [settings, setSettings] = useState<Record<string, NovelSettingRecord>>({});
  const [stepContent, setStepContent] = useState<Record<string, string>>({});
  const [stepTitles, setStepTitles] = useState<Record<string, string>>({});
  const [stepStructured, setStepStructured] = useState<Record<string, any>>({});
  const [saving, setSaving] = useState(false);
  const [loadingExisting, setLoadingExisting] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const autoGenTriggered = useRef<Record<string, boolean>>({});

  const {
    streamingText,
    statusMessage,
    isStreaming,
    error: streamError,
    generate,
    stop,
  } = useSettingStream();

  const isFinalStep = step === FINAL_STEP_INDEX;
  const currentType = !isFinalStep ? WIZARD_STEP_TYPES[step] : '';
  const currentLabel = wizardSteps[step];
  const currentPresets = STEP_PRESETS[currentLabel] || [];
  const currentContent = currentType ? stepContent[currentType] ?? '' : '';
  const currentTitle = currentType ? stepTitles[currentType] ?? '' : '';
  const currentStructured = currentType ? stepStructured[currentType] ?? {} : {};

  const updateCurrentContent = (value: string) => {
    if (!currentType) return;
    setStepContent((prev) => ({ ...prev, [currentType]: value }));
  };

  const updateCurrentTitle = (value: string) => {
    if (!currentType) return;
    setStepTitles((prev) => ({ ...prev, [currentType]: value }));
  };

  const updateStructuredField = (field: string, value: any) => {
    if (!currentType) return;
    setStepStructured((prev) => ({
      ...prev,
      [currentType]: { ...(prev[currentType] || {}), [field]: value },
    }));
  };

  // Load any previously-saved draft settings on open
  useEffect(() => {
    if (!open || !draftId) return;
    let cancelled = false;
    setLoadingExisting(true);
    getDraftSettings(draftId)
      .then((res) => {
        if (cancelled) return;
        const list = pickArray(res);
        const map: Record<string, NovelSettingRecord> = {};
        const contentMap: Record<string, string> = {};
        const titleMap: Record<string, string> = {};
        const structMap: Record<string, any> = {};
        list.forEach((item: NovelSettingRecord) => {
          map[item.setting_type] = item;
          contentMap[item.setting_type] = item.content || '';
          titleMap[item.setting_type] = item.title || '';
          structMap[item.setting_type] = item.structured_data || {};
          autoGenTriggered.current[item.setting_type] = true;
        });
        setSettings(map);
        setStepContent(contentMap);
        setStepTitles(titleMap);
        setStepStructured(structMap);
      })
      .catch(() => {
        if (!cancelled) {
          setSettings({});
          setStepContent({});
          setStepTitles({});
          setStepStructured({});
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingExisting(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, draftId]);

  // Reset on close
  useEffect(() => {
    if (!open) {
      setStep(0);
      setSettings({});
      setStepContent({});
      setStepTitles({});
      setStepStructured({});
      autoGenTriggered.current = {};
      stop();
    }
  }, [open, stop]);

  const buildPriorSettings = useCallback(
    (forStep: number) => {
      const prior: any[] = [];
      for (let i = 0; i < forStep; i++) {
        const type = WIZARD_STEP_TYPES[i];
        const content = stepContent[type];
        const structured = stepStructured[type];
        if (content || structured) {
          prior.push({
            setting_type: type,
            title: stepTitles[type] || wizardSteps[i],
            content: content || '',
            structured_data: structured || {},
          });
        }
      }
      return prior;
    },
    [stepContent, stepTitles, stepStructured],
  );

  const buildContextString = useCallback(
    (forStep: number) => {
      const prior: string[] = [];
      if (pendingTitle) prior.push(`书名灵感:${pendingTitle}`);
      for (let i = 0; i < forStep; i++) {
        const type = WIZARD_STEP_TYPES[i];
        const content = stepContent[type];
        if (content) {
          prior.push(`【${wizardSteps[i]}】\n${content}`);
        }
      }
      return prior.join('\n\n');
    },
    [pendingTitle, stepContent],
  );

  const runGenerate = useCallback(
    async (targetStep: number) => {
      const type = WIZARD_STEP_TYPES[targetStep];
      const label = wizardSteps[targetStep];
      if (!type) return;
      try {
        const res = await generate({
          setting_type: type,
          book_title: pendingTitle || '新书',
          genre: '',
          context: buildContextString(targetStep) || pendingTitle || label,
          prior_settings: buildPriorSettings(targetStep),
        });
        if (!res) {
          message.warning('AI 未返回内容,请重试或手动填写');
          return;
        }
        setStepContent((prev) => ({ ...prev, [type]: res.content }));
        setStepTitles((prev) => ({ ...prev, [type]: prev[type] || res.title || label }));
        setStepStructured((prev) => ({ ...prev, [type]: res.structured_data || {} }));
        if (res.validation_ok) {
          message.success(`已生成${label}`);
        } else {
          message.warning(`${label}生成成功, 但结构校验未通过, 可手动修正`);
        }
      } catch (err: any) {
        console.error(err);
        message.error(err?.message || `${label}生成失败`);
      }
    },
    [generate, pendingTitle, buildContextString, buildPriorSettings],
  );

  // Keep a stable ref to runGenerate so the auto-generate effect
  // doesn't re-fire when runGenerate's dependencies change.
  const runGenerateRef = useRef(runGenerate);
  runGenerateRef.current = runGenerate;

  // Auto-generate on entering a non-final step that has no content yet
  useEffect(() => {
    if (!open || loadingExisting) return;
    if (isFinalStep) return;
    if (!draftId) return;
    if (isStreaming) return;
    const type = WIZARD_STEP_TYPES[step];
    if (!type) return;
    if (stepContent[type]) return;
    if (autoGenTriggered.current[type]) return;
    autoGenTriggered.current[type] = true;
    void runGenerateRef.current(step);
  }, [open, loadingExisting, isFinalStep, draftId, step, stepContent, isStreaming]);

  const handleManualGenerate = async () => {
    if (!currentType) return;
    autoGenTriggered.current[currentType] = true;
    await runGenerate(step);
  };

  const handlePresetClick = (preview: string, title: string) => {
    if (!currentType) return;
    setStepContent((prev) => ({
      ...prev,
      [currentType]: prev[currentType]
        ? `${prev[currentType]}\n\n${preview}`
        : preview,
    }));
    setStepTitles((prev) => ({
      ...prev,
      [currentType]: prev[currentType] || title,
    }));
  };

  const persistCurrent = async (): Promise<boolean> => {
    if (!draftId || !currentType) return true;
    const contentValue = (stepContent[currentType] ?? '').trim();
    if (!contentValue) {
      message.warning('请先生成或填写内容');
      return false;
    }
    setSaving(true);
    try {
      const payload = {
        setting_type: currentType,
        title: stepTitles[currentType] || currentLabel,
        content: stepContent[currentType] ?? '',
        structured_data: stepStructured[currentType] || {},
      };
      const saved = await saveDraftStep(draftId, payload);
      const record: NovelSettingRecord = {
        setting_type: currentType,
        title: saved?.title || payload.title,
        content: saved?.content || payload.content,
        structured_data: saved?.structured_data || payload.structured_data,
      };
      setSettings((prev) => ({ ...prev, [currentType]: record }));
      return true;
    } catch (err: any) {
      console.error(err);
      message.error(err?.response?.data?.detail || '保存失败');
      return false;
    } finally {
      setSaving(false);
    }
  };

  const handleNext = async () => {
    const ok = await persistCurrent();
    if (!ok) return;
    setStep((s) => Math.min(s + 1, FINAL_STEP_INDEX));
  };

  const handlePrev = () => {
    setStep((s) => Math.max(s - 1, 0));
  };

  const handleFinish = async () => {
    if (!draftId) return;
    setFinishing(true);
    try {
      const project = await completeDraft(draftId);
      message.success('已完成新书设置,进入工作台');
      onFinished(project?.id);
    } catch (err: any) {
      console.error(err);
      message.error(err?.response?.data?.detail || '完成向导失败');
    } finally {
      setFinishing(false);
    }
  };

  const savedKeys = useMemo(() => new Set(Object.keys(settings)), [settings]);
  const completionRate = useMemo(() => {
    if (WIZARD_STEP_TYPES.length === 0) return 0;
    return Math.round((savedKeys.size / WIZARD_STEP_TYPES.length) * 100);
  }, [savedKeys]);

  const stepItems = useMemo(
    () =>
      wizardSteps.map((title, idx) => {
        const type = WIZARD_STEP_TYPES[idx];
        const saved = savedKeys.has(type);
        return {
          title,
          subTitle: saved ? (
            <span className="text-xs text-emerald-500">已保存</span>
          ) : (
            <span className="text-xs text-gray-400">待生成</span>
          ),
        };
      }),
    [savedKeys],
  );

  const previewMarkdown = isStreaming ? streamingText : currentContent;
  const canProceed = !isStreaming && (!!currentContent || isFinalStep);

  const handleExportWizard = async () => {
    const text = WIZARD_STEP_TYPES.map((type, idx) => {
      const rec = settings[type];
      const fallback = stepContent[type] || '';
      const title = rec?.title || stepTitles[type] || wizardSteps[idx];
      return `${idx + 1}. ${wizardSteps[idx]} · ${title}\n${rec?.content || fallback}`;
    }).join('\n\n');
    if (!text.trim()) {
      message.warning('暂无可导出的内容');
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      message.success('已复制全部设定');
    } catch {
      message.warning('复制失败, 请手动选中文本');
    }
  };

  // ------------------------- 可视化渲染 -------------------------

  const renderWorldviewCards = () => {
    const dims = [
      { key: 'time_setting', label: '时间设定', hint: '故事发生的年代' },
      { key: 'place_setting', label: '地点设定', hint: '地理环境与空间布局' },
      { key: 'social_structure', label: '社会结构', hint: '政治 / 经济 / 阶层' },
      { key: 'cultural_background', label: '文化背景', hint: '语言 / 宗教 / 艺术 / 习俗' },
      { key: 'tech_level', label: '科技水平', hint: '技术对生活的影响' },
      { key: 'power_system', label: '力量体系', hint: '魔法 / 科技 / 超能力规则' },
      { key: 'history', label: '历史背景', hint: '世界的历史沿革' },
      { key: 'natural_laws', label: '自然法则', hint: '物理规律 / 运行铁律' },
    ];
    return (
      <div className="grid grid-cols-2 gap-3">
        {dims.map((d) => (
          <div key={d.key} className="bg-slate-50 rounded-2xl p-3 border border-slate-100">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-indigo-600">{d.label}</span>
              <span className="text-[10px] text-gray-400">{d.hint}</span>
            </div>
            <TextArea
              autoSize={{ minRows: 3, maxRows: 5 }}
              value={currentStructured[d.key] || ''}
              onChange={(e) => updateStructuredField(d.key, e.target.value)}
              placeholder={`等待 AI 生成${d.label}...`}
              className="text-xs"
            />
          </div>
        ))}
      </div>
    );
  };

  const renderMapGraph = () => {
    const regions: any[] = Array.isArray(currentStructured.regions)
      ? currentStructured.regions
      : [];
    if (!regions.length) {
      return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="等待 AI 生成地图" />;
    }
    const nodes = regions.map((r) => ({
      name: r.name || '未命名',
      symbolSize: 44,
      itemStyle: { color: '#6366f1' },
      tooltip: { formatter: () => `${r.name}<br/>${r.description || ''}` },
    }));
    const links: any[] = [];
    regions.forEach((r) => {
      (r.connected_to || []).forEach((target: string) => {
        if (regions.find((x) => x.name === target)) {
          links.push({ source: r.name, target });
        }
      });
    });
    const option = {
      tooltip: {},
      series: [
        {
          type: 'graph',
          layout: 'force',
          roam: true,
          label: { show: true, color: '#1e293b' },
          force: { repulsion: 280, edgeLength: [80, 180] },
          data: nodes,
          links,
          lineStyle: { color: '#c4b5fd', width: 1.4, curveness: 0.1 },
        },
      ],
    };
    return (
      <div className="space-y-3">
        <ReactECharts option={option} style={{ height: 280 }} />
        <div className="space-y-2 max-h-48 overflow-auto pr-1">
          {regions.map((r, idx) => (
            <div key={idx} className="border border-slate-200 rounded-xl p-2 bg-white">
              <Input
                size="small"
                value={r.name || ''}
                onChange={(e) => {
                  const next = [...regions];
                  next[idx] = { ...next[idx], name: e.target.value };
                  updateStructuredField('regions', next);
                }}
                placeholder="地区名"
                className="mb-1"
              />
              <TextArea
                size="small"
                autoSize={{ minRows: 1, maxRows: 3 }}
                value={r.description || ''}
                onChange={(e) => {
                  const next = [...regions];
                  next[idx] = { ...next[idx], description: e.target.value };
                  updateStructuredField('regions', next);
                }}
                placeholder="地区描述"
              />
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderPlotArcSteps = () => {
    const acts: any[] = Array.isArray(currentStructured.acts) ? currentStructured.acts : [];
    if (!acts.length) {
      return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="等待 AI 生成情节弧" />;
    }
    return (
      <div className="space-y-3">
        <Steps
          orientation="horizontal"
          current={acts.length}
          items={acts.map((a: any, idx: number) => ({
            title: a.name || `第${idx + 1}幕`,
            subTitle: (
              <span className="text-[11px] text-gray-500">
                {(a.key_events || []).slice(0, 1).join(' · ')}
              </span>
            ),
          }))}
        />
        <div className="space-y-2 max-h-48 overflow-auto pr-1">
          {acts.map((a, idx) => (
            <div key={idx} className="border border-slate-200 rounded-xl p-2 bg-white">
              <Input
                size="small"
                value={a.name || ''}
                onChange={(e) => {
                  const next = [...acts];
                  next[idx] = { ...next[idx], name: e.target.value };
                  updateStructuredField('acts', next);
                }}
                placeholder="幕名"
                className="mb-1"
              />
              <TextArea
                size="small"
                autoSize={{ minRows: 1, maxRows: 3 }}
                value={a.description || ''}
                onChange={(e) => {
                  const next = [...acts];
                  next[idx] = { ...next[idx], description: e.target.value };
                  updateStructuredField('acts', next);
                }}
                placeholder="幕描述"
              />
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderCharacterCards = () => {
    const list: any[] = Array.isArray(currentStructured.characters)
      ? currentStructured.characters
      : [];
    if (!list.length) {
      return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="等待 AI 生成角色" />;
    }
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-2 max-h-96 overflow-auto pr-1">
        {list.map((c, idx) => (
          <div key={idx} className="border border-slate-200 rounded-xl p-3 bg-white">
            <div className="flex items-center justify-between mb-2">
              <Input
                size="small"
                value={c.name || ''}
                onChange={(e) => {
                  const next = [...list];
                  next[idx] = { ...next[idx], name: e.target.value };
                  updateStructuredField('characters', next);
                }}
                placeholder="角色名"
                className="flex-1 mr-2"
              />
              <Tag color="purple">{c.role || '未定角色'}</Tag>
            </div>
            <TextArea
              size="small"
              autoSize={{ minRows: 2, maxRows: 4 }}
              value={c.brief || c.motivation || ''}
              onChange={(e) => {
                const next = [...list];
                const key = next[idx].brief !== undefined ? 'brief' : 'motivation';
                next[idx] = { ...next[idx], [key]: e.target.value };
                updateStructuredField('characters', next);
              }}
              placeholder="角色简介 / 动机"
            />
          </div>
        ))}
      </div>
    );
  };

  const renderStructuredEditor = () => {
    if (currentType === 'worldview') return renderWorldviewCards();
    if (currentType === 'map') return renderMapGraph();
    if (currentType === 'plot_arc') return renderPlotArcSteps();
    if (currentType === 'characters' || currentType === 'main_characters') {
      return renderCharacterCards();
    }
    // fallback: plain textarea on content
    return (
      <TextArea
        rows={16}
        placeholder={`补充或修改${currentLabel}的具体设定...`}
        value={currentContent}
        onChange={(e) => updateCurrentContent(e.target.value)}
      />
    );
  };

  return (
    <Modal
      open={open}
      centered
      width={1300}
      styles={{
        body: { padding: 0 },
      }}
      style={{ top: 16 }}
      title={null}
      onCancel={onClose}
      footer={null}
      destroyOnClose
    >
      <div className="p-4 lg:p-6 space-y-4 bg-slate-50">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold text-slate-800">新书设置向导</h2>
          {pendingTitle && <Tag color="purple">{pendingTitle}</Tag>}
          <Tag color="blue">
            第 {step + 1} / {wizardSteps.length} 步 · {currentLabel}
          </Tag>
          <Tag color={draftId ? 'green' : 'default'}>
            {draftId ? `草稿 #${draftId}` : '未创建草稿'}
          </Tag>
        </div>
        <div className="flex flex-col xl:flex-row gap-4 h-[74vh]">
          <aside className="w-full xl:w-72 flex-shrink-0">
            <div className="rounded-3xl border bg-white h-full p-4 flex flex-col">
              <div className="flex items-center justify-between mb-3">
                <span className="font-medium text-slate-800">步骤导航</span>
                <Tag color={completionRate >= 80 ? 'green' : 'blue'}>{completionRate}%</Tag>
              </div>
              <Steps
                orientation="vertical"
                size="small"
                current={step}
                onChange={(value) => setStep(value)}
                items={stepItems}
                className="flex-1 pr-1 overflow-y-auto"
              />
              <div className="pt-4 space-y-2 text-xs text-gray-500">
                <p>提示：每步进入时将自动通过 WebSocket 流式生成内容；可随时点击重新生成。</p>
                <Button
                  block
                  size="small"
                  icon={<ThunderboltOutlined />}
                  onClick={handleManualGenerate}
                  disabled={isStreaming || isFinalStep}
                >
                  重新生成当前步
                </Button>
              </div>
            </div>
          </aside>
          <section className="flex-1 flex flex-col">
            <div className="rounded-3xl border bg-white h-full p-4 flex flex-col">
              {loadingExisting ? (
                <div className="flex items-center justify-center flex-1">
                  <Spin description="加载已保存内容..." />
                </div>
              ) : isFinalStep ? (
                <div className="flex flex-col h-full">
                  <div className="flex items-center justify-between mb-4">
                    <p className="text-sm text-gray-600">
                      以下为《{pendingTitle || '新书'}》的完整设定，请确认后点击"完成并进入工作台"。
                    </p>
                    <Button onClick={handleExportWizard} size="small">
                      导出设定
                    </Button>
                  </div>
                  <div className="flex-1 overflow-y-auto pr-2 space-y-4">
                    {WIZARD_STEP_TYPES.map((type, idx) => {
                      const rec = settings[type];
                      const pending = stepContent[type];
                      const displayTitle = rec?.title || stepTitles[type] || wizardSteps[idx];
                      const displayContent = rec?.content || pending || '';
                      return (
                        <div key={type} className="border border-slate-200 rounded-2xl p-4">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-semibold text-slate-800">
                              {idx + 1}. {wizardSteps[idx]} · {displayTitle}
                            </span>
                            {!rec && <Tag color="orange">未保存</Tag>}
                          </div>
                          {displayContent ? (
                            <div data-color-mode="light" className="text-sm">
                              <MDEditor.Markdown source={displayContent} style={{ background: 'transparent' }} />
                            </div>
                          ) : (
                            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无内容" />
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="flex flex-col lg:flex-row gap-4 flex-1 overflow-hidden">
                  <div className="flex-1 flex flex-col">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <p className="text-sm font-medium text-gray-700">AI 实时输出</p>
                        {isStreaming && (
                          <p className="text-xs text-emerald-500 flex items-center gap-1">
                            <PlayCircleOutlined className="animate-pulse" />
                            {statusMessage || 'WebSocket 流式生成中'}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {isStreaming && (
                          <Tooltip title="停止接收当前流">
                            <Button
                              icon={<PauseOutlined />}
                              size="small"
                              onClick={stop}
                              danger
                              ghost
                            >
                              停止
                            </Button>
                          </Tooltip>
                        )}
                        <Button
                          type="primary"
                          size="small"
                          loading={isStreaming}
                          icon={<ThunderboltOutlined />}
                          onClick={handleManualGenerate}
                        >
                          重新生成
                        </Button>
                      </div>
                    </div>
                    <div className="bg-white border border-slate-200 text-slate-800 text-sm rounded-2xl p-4 flex-1 overflow-auto whitespace-pre-wrap" data-color-mode="light">
                      {streamError && !isStreaming ? (
                        <div className="flex flex-col items-center justify-center h-full gap-2">
                          <p className="text-red-500 text-sm">{streamError}</p>
                          <Button size="small" type="primary" onClick={handleManualGenerate}>
                            重试
                          </Button>
                        </div>
                      ) : isStreaming && !previewMarkdown ? (
                        <div className="flex flex-col items-center justify-center h-full gap-2">
                          <Spin description={statusMessage || `正在生成${currentLabel}...`} />
                          {statusMessage && (
                            <p className="text-xs text-gray-400 mt-2 animate-pulse">{statusMessage}</p>
                          )}
                        </div>
                      ) : previewMarkdown ? (
                        <MDEditor.Markdown source={previewMarkdown} style={{ background: 'transparent' }} />
                      ) : (
                        <p className="text-xs text-gray-400">
                          进入本步后将自动基于前序设定生成建议；也可点击右上角重新生成或使用下方预设。
                        </p>
                      )}
                    </div>
                    {currentPresets.length > 0 && (
                      <div className="mt-3">
                        <p className="text-xs text-gray-500 mb-2">快速选项</p>
                        <div className="flex flex-wrap gap-2">
                          {currentPresets.map((preset) => (
                            <Button key={preset.title} size="small" onClick={() => handlePresetClick(preset.preview, preset.title)}>
                              {preset.title}
                            </Button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="flex-1 flex flex-col overflow-hidden">
                    <span className="text-sm font-medium text-gray-700 mb-2">结构化编辑</span>
                    <Input
                      placeholder={`${currentLabel}标题`}
                      value={currentTitle}
                      onChange={(e) => updateCurrentTitle(e.target.value)}
                      className="mb-2"
                    />
                    <div className="flex-1 overflow-auto">{renderStructuredEditor()}</div>
                  </div>
                </div>
              )}
            </div>
          </section>
        </div>
        <div className="flex items-center justify-between">
          <Button disabled={step === 0 || saving || finishing || isStreaming} onClick={handlePrev}>
            上一步
          </Button>
          <div className="flex items-center gap-3">
            <Progress percent={completionRate} size="small" style={{ width: 160 }} />
            {isFinalStep ? (
              <Button type="primary" loading={finishing} onClick={handleFinish}>
                完成并进入工作台
              </Button>
            ) : (
              <Button type="primary" loading={saving} disabled={!canProceed} onClick={handleNext}>
                下一步
              </Button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
};
