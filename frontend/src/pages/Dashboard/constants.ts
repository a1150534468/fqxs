export const wizardSteps = [
  '世界观',
  '人物',
  '地图',
  '故事线',
  '情节弧',
  '开始',
  '进入工作台',
];

export const WIZARD_STEP_TYPES = [
  'worldview',
  'characters',
  'map',
  'storyline',
  'plot_arc',
  'opening',
];

export const statusColors: Record<string, string> = {
  active: 'green',
  paused: 'orange',
  completed: 'blue',
  abandoned: 'red',
};

export const chapterStatusTag: Record<string, { color: string; label: string }> = {
  generating: { color: 'processing', label: '生成中' },
  pending_review: { color: 'warning', label: '待审核' },
  approved: { color: 'green', label: '已审核' },
  published: { color: 'blue', label: '已发布' },
  failed: { color: 'red', label: '失败' },
};

export const formatNumber = (value: number | undefined) => {
  if (!value) return 0;
  return value.toLocaleString('zh-CN');
};
