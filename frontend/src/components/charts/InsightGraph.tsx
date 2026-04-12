import React from 'react';
import ReactECharts from 'echarts-for-react';

interface InsightGraphProps {
  projects: { title: string; progress?: number; status?: string }[];
  inspirations: { title: string; hot_score?: number }[];
}

const categoryColors = ['#7c3aed', '#0ea5e9', '#f97316'];

export const InsightGraph: React.FC<InsightGraphProps> = ({ projects, inspirations }) => {
  if (projects.length === 0 && inspirations.length === 0) {
    return (
      <div className="h-[320px] flex items-center justify-center text-gray-400">
        暂无数据，等待生成记录...
      </div>
    );
  }

  const anchorNode = { name: 'AI调度节点', category: 0, symbolSize: 48, value: 100 };
  const projectNodes = projects.map((project) => ({
    name: `P·${project.title}`,
    displayName: project.title,
    category: 1,
    value: project.progress ?? 0,
    symbolSize: 26 + Math.min(project.progress ?? 0, 40) / 2,
    itemStyle: { color: categoryColors[1] },
  }));

  const inspirationNodes = inspirations.map((insp) => ({
    name: `I·${insp.title}`,
    displayName: insp.title,
    category: 2,
    value: insp.hot_score ?? 0,
    symbolSize: 20 + Math.min(Number(insp.hot_score) || 0, 30) / 3,
    itemStyle: { color: categoryColors[2] },
  }));

  const nodes = [anchorNode, ...projectNodes, ...inspirationNodes];

  const links = [
    ...projectNodes.map((_node) => ({
      source: anchorNode.name,
      target: _node.name,
      value: _node.value,
    })),
    ...inspirationNodes.map((_node, index) => ({
      source: _node.name,
      target: projectNodes[index % Math.max(projectNodes.length, 1)]?.name || anchorNode.name,
      value: _node.value,
    })),
  ];

  const option = {
    tooltip: {
      formatter: (params: any) => {
        if (params.dataType === 'node' && params.data.displayName) {
          return `${params.data.displayName}<br/>热度/进度：${params.data.value}`;
        }
        return params.name;
      },
    },
    legend: {
      data: ['AI调度', '项目', '灵感'],
      textStyle: { color: '#6b7280' },
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        label: {
          show: true,
          formatter: (params: any) => params.data.displayName || params.name.replace(/^[PI]·/, ''),
          color: '#374151',
        },
        force: {
          repulsion: 260,
          edgeLength: [50, 200],
        },
        data: nodes,
        links,
        categories: [
          { name: 'AI调度', itemStyle: { color: categoryColors[0] } },
          { name: '项目', itemStyle: { color: categoryColors[1] } },
          { name: '灵感', itemStyle: { color: categoryColors[2] } },
        ],
        lineStyle: {
          color: '#c4b5fd',
          width: 1.2,
          opacity: 0.8,
        },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: 320 }} />;
};
