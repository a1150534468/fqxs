import React from 'react';
import ReactECharts from 'echarts-for-react';

interface PieChartProps {
  title?: string;
  data: { name: string; value: number }[];
}

export const PieChart: React.FC<PieChartProps> = ({ title, data }) => {
  const options = {
    title: {
      text: title,
      textStyle: { fontSize: 14, fontWeight: 'normal' },
      left: 'center'
    },
    tooltip: {
      trigger: 'item'
    },
    legend: {
      bottom: '5%',
      left: 'center'
    },
    series: [
      {
        name: '生成状态',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 20,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: data
      }
    ]
  };

  return <ReactECharts option={options} style={{ height: 300, width: '100%' }} />;
};
