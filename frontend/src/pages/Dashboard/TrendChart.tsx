import React from 'react';
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';

const TrendChart: React.FC = () => {
  const option = {
    title: {
      text: 'Last 7 Days Read Count',
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'normal',
        color: '#374151'
      }
    },
    tooltip: {
      trigger: 'axis'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      axisLine: {
        lineStyle: {
          color: '#9CA3AF'
        }
      }
    },
    yAxis: {
      type: 'value',
      axisLine: {
        show: false
      },
      splitLine: {
        lineStyle: {
          color: '#E5E7EB',
          type: 'dashed'
        }
      }
    },
    series: [
      {
        name: 'Reads',
        type: 'line',
        stack: 'Total',
        smooth: true,
        lineStyle: {
          width: 3,
          color: '#3B82F6'
        },
        showSymbol: false,
        areaStyle: {
          opacity: 0.8,
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            {
              offset: 0,
              color: 'rgba(59, 130, 246, 0.5)'
            },
            {
              offset: 1,
              color: 'rgba(59, 130, 246, 0.1)'
            }
          ])
        },
        data: [120, 132, 101, 134, 90, 230, 210]
      }
    ]
  };

  return <ReactECharts option={option} style={{ height: '350px', width: '100%' }} />;
};

export default TrendChart;