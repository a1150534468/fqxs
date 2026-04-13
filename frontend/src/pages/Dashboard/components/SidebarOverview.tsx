import { Card, List, Tag, Button } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';

interface SidebarOverviewProps {
  stats: { label: string; value: string | number }[];
  onCreateProject: () => void;
}

export const SidebarOverview = ({ stats, onCreateProject }: SidebarOverviewProps) => (
  <div className="space-y-4 lg:sticky lg:top-8">
    <Card className="bg-gradient-to-br from-[#2b1a5a] to-[#4c1d95] text-white border-none shadow-xl rounded-3xl">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-indigo-200">林亦苏 · 小封博</p>
          <h3 className="text-xl font-semibold mt-1">690 位粉丝关注</h3>
          <p className="text-xs text-indigo-100 mt-3">保持每日 1 章更新 · 审核改写 ≥15%</p>
        </div>
        <Tag color="gold" className="text-sm py-1 px-3 rounded-full border-none bg-white/15">LIVE</Tag>
      </div>
      <Button
        type="primary"
        icon={<ThunderboltOutlined />}
        className="mt-4 w-full"
        size="large"
        onClick={onCreateProject}
      >
        新书建档
      </Button>
    </Card>

    <Card className="shadow-md rounded-2xl">
      <List
        dataSource={stats}
        renderItem={(item) => (
          <List.Item className="flex justify-between py-2">
            <span className="text-gray-500 text-sm">{item.label}</span>
            <span className="text-lg font-semibold text-slate-900">{item.value}</span>
          </List.Item>
        )}
      />
    </Card>

    <Card className="shadow-md rounded-2xl">
      <h4 className="text-sm text-gray-500 mb-2">系统通知</h4>
      <p className="text-sm text-gray-700">
        直播房“星港逐梦”预约满员，今晚 20:00 将自动推送维度框架回放，记得前往知识库查收。
      </p>
    </Card>
  </div>
);
