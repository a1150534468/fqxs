import { Button, Card, Col, Empty, Input, Popconfirm, Row, Tag } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { statusColors } from '../constants';
import type { Novel } from '../types';

const { Search } = Input;

interface BookGridProps {
  novels: Novel[];
  onSelectNovel: (novelId: number) => void;
  onDeleteNovel?: (novelId: number) => void;
}

export const BookGrid = ({ novels, onSelectNovel, onDeleteNovel }: BookGridProps) => {
  const statusLabel: Record<string, string> = {
    active: '连载中',
    paused: '已暂停',
    completed: '已完结',
    abandoned: '已废弃',
    planning: '规划中',
  };

  return (
    <Card
      className="shadow-md"
      title={
        <div className="flex items-center gap-2">
          <span>我的书目</span>
          <Tag className="ml-1">{novels.length} 本</Tag>
        </div>
      }
      extra={<Search placeholder="搜索书目..." size="small" style={{ width: 160 }} />}
    >
      {novels.length === 0 ? (
        <Empty description="尚无书目，快建档吧！" />
      ) : (
        <>
          <div className="hidden md:block">
            <Row gutter={[16, 16]}>
              {novels.map((novel) => (
                <Col span={8} key={novel.id}>
                  <BookCard novel={novel} onSelect={onSelectNovel} onDelete={onDeleteNovel} statusLabel={statusLabel} />
                </Col>
              ))}
            </Row>
          </div>
          <div className="md:hidden flex gap-4 overflow-x-auto pb-2 snap-x snap-mandatory">
            {novels.map((novel) => (
              <div className="min-w-[240px] snap-start" key={novel.id}>
                <BookCard novel={novel} onSelect={onSelectNovel} onDelete={onDeleteNovel} statusLabel={statusLabel} />
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  );
};

interface BookCardProps {
  novel: Novel;
  onSelect: (id: number) => void;
  onDelete?: (id: number) => void;
  statusLabel: Record<string, string>;
}

const BookCard = ({ novel, onSelect, onDelete, statusLabel }: BookCardProps) => (
  <Card
    hoverable
    className="shadow-sm h-full rounded-2xl"
    bodyStyle={{ padding: 16 }}
    onClick={() => onSelect(novel.id)}
  >
    <div className="flex items-start justify-between">
      <div className="flex-1 min-w-0">
        <p className="font-bold text-base text-gray-900 truncate">{novel.title}</p>
        <p className="text-xs text-gray-400 mt-1">{novel.genre || '未分类'}</p>
      </div>
      {onDelete && (
        <Popconfirm
          title="删除书目"
          description={`确定删除《${novel.title}》吗？`}
          okText="删除"
          cancelText="取消"
          okButtonProps={{ danger: true }}
          onConfirm={(e) => {
            e?.stopPropagation();
            onDelete(novel.id);
          }}
          onCancel={(e) => e?.stopPropagation()}
        >
          <Button
            type="text"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={(e) => {
              e.stopPropagation();
            }}
          />
        </Popconfirm>
      )}
    </div>
    <div className="mt-3 flex items-center justify-between">
      <Tag color={novel.status === 'planning' ? 'purple' : statusColors[novel.status || 'active'] || 'default'}>
        {statusLabel[novel.status || 'active'] || novel.status || 'active'}
      </Tag>
      {novel.current_chapter && (
        <span className="text-xs text-gray-400">已写 {novel.current_chapter} 章</span>
      )}
    </div>
  </Card>
);
