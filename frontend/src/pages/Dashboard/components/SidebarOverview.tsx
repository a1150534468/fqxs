import { Card, List } from 'antd';

interface SidebarOverviewProps {
  stats: { label: string; value: string | number }[];
  onCreateProject: () => void;
}

export const SidebarOverview = ({ stats }: SidebarOverviewProps) => (
  <div className="space-y-4 lg:sticky lg:top-8">
  

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
        1111
      </p>
    </Card>
  </div>
);
