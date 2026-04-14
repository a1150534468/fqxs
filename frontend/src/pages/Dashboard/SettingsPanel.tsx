import React, { useMemo } from 'react';
import { Empty, Tabs } from 'antd';
import MDEditor from '@uiw/react-md-editor';
import { InsightGraph } from '../../components/charts/InsightGraph';
import type { KnowledgeGraphPayload, NovelSettingRecord } from './types';
import { WIZARD_STEP_TYPES } from './constants';

const STEP_LABELS: Record<string, string> = {
  worldview: '世界观',
  characters: '角色',
  map: '地图',
  storyline: '故事线',
  plot_arc: '情节弧',
  opening: '开篇',
};

interface SettingsPanelProps {
  settings: NovelSettingRecord[];
  knowledgeGraph?: KnowledgeGraphPayload;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({ settings, knowledgeGraph }) => {
  const settingsMap = useMemo(() => {
    const map: Record<string, NovelSettingRecord> = {};
    settings.forEach((s) => { map[s.setting_type] = s; });
    return map;
  }, [settings]);

  const tabItems = WIZARD_STEP_TYPES.map((type) => ({
    key: type,
    label: STEP_LABELS[type] || type,
    children: settingsMap[type] ? (
      <div className="overflow-y-auto" style={{ maxHeight: 260 }}>
        <MDEditor.Markdown source={settingsMap[type].content || '暂无内容'} />
      </div>
    ) : (
      <Empty description="暂未生成，请先通过向导完成设定" image={Empty.PRESENTED_IMAGE_SIMPLE} />
    ),
  }));

  const graphProjects = useMemo(() => {
    if (knowledgeGraph?.nodes) {
      const plotNodes = knowledgeGraph.nodes.filter((n) => n.category === 'plot');
      if (plotNodes.length) return plotNodes.map((n) => ({ title: n.name, status: n.category }));
    }
    return [];
  }, [knowledgeGraph]);

  const graphInspirations = useMemo(() => {
    if (knowledgeGraph?.nodes) {
      const chars = knowledgeGraph.nodes.filter((n) => n.category === 'character');
      if (chars.length) return chars.map((n) => ({ title: n.name, hot_score: Number(n.info?.influence) || 0 }));
    }
    return [];
  }, [knowledgeGraph]);

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Settings tabs */}
      <div className="rounded-lg border border-gray-200 bg-white p-3">
        <Tabs size="small" items={tabItems} />
      </div>

      {/* Knowledge graph */}
      <div className="rounded-lg border border-gray-200 bg-white p-3">
        <div className="text-xs font-medium text-gray-500 mb-2">知识图谱</div>
        {graphProjects.length || graphInspirations.length ? (
          <InsightGraph projects={graphProjects} inspirations={graphInspirations} />
        ) : (
          <Empty description="暂无图谱数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </div>
    </div>
  );
};
