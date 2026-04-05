import React from 'react';
import ReactECharts from 'echarts-for-react';

interface BarChartProps {
  title?: string;
  data: { category: string; value: number }[];
  color?: string;
}

export const BarChart: React.FC<BarChartProps> = ({ title, data, color = '#10b981' }) => {
  const options = {
    title: {
      text: title,
      textStyle: { fontSize: 14, fontWeight: 'normal' },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: data.map(item => item.category),
    },
    yAxis: {
      type: 'value',
    },
    series: [
      {
        name: '收益',
        type: 'bar',
        data: data.map(item => item.value),
        itemStyle: { color, borderRadius: [4, 4, 0, 0] },
      },
    ],
  };

  return <ReactECharts option={options} style={{ height: 300, width: '100%' }} />;
};
