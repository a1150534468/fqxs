import React from 'react';
import ReactECharts from 'echarts-for-react';

interface LineChartProps {
  title?: string;
  data: { date: string; value: number }[];
  color?: string;
}

export const LineChart: React.FC<LineChartProps> = ({ title, data, color = '#3b82f6' }) => {
  const options = {
    title: {
      text: title,
      textStyle: { fontSize: 14, fontWeight: 'normal' },
    },
    tooltip: {
      trigger: 'axis',
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.map(item => item.date),
    },
    yAxis: {
      type: 'value',
    },
    series: [
      {
        name: '阅读量',
        type: 'line',
        smooth: true,
        data: data.map(item => item.value),
        itemStyle: { color },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: `${color}80` }, // 50% opacity
              { offset: 1, color: `${color}00` }  // 0% opacity
            ],
          }
        }
      },
    ],
  };

  return <ReactECharts option={options} style={{ height: 300, width: '100%' }} />;
};
