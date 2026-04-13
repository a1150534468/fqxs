import { Button, Card, Input } from 'antd';

const { TextArea } = Input;

export interface ChatMessage {
  id: string;
  role: 'user' | 'ai';
  text: string;
  timestamp: string;
}

interface NewBookCardProps {
  chatInput: string;
  setChatInput: (value: string) => void;
  onCreateProject: () => void;
  history: ChatMessage[];
}

export const NewBookCard = ({ chatInput, setChatInput, onCreateProject, history }: NewBookCardProps) => (
  <Card className="shadow-xl border-none rounded-3xl h-full flex flex-col">
    <div className="flex items-center justify-between mb-4">
      <div>
        <p className="text-sm text-gray-500">新建书目</p>
        <h3 className="text-xl font-semibold text-gray-900">输入灵感 · 拉起 12 步向导</h3>
      </div>
      <Button type="link" onClick={onCreateProject}>
        高级设置
      </Button>
    </div>

    <div className="flex-1 bg-slate-50 rounded-2xl p-4 mb-4 overflow-hidden">
      <div className="h-56 overflow-y-auto pr-2 space-y-3 scroll-smooth">
        {history.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm shadow-sm ${
                message.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-br-sm'
                  : 'bg-white text-gray-700 rounded-bl-sm'
              }`}
            >
              <p className="font-medium text-xs mb-1">{message.role === 'user' ? '我' : 'PlotPilot'}</p>
              <p className="leading-relaxed whitespace-pre-wrap">{message.text}</p>
              <p className="text-[10px] opacity-70 text-right mt-1">{message.timestamp}</p>
            </div>
          </div>
        ))}
      </div>
    </div>

    <TextArea
      rows={4}
      placeholder="输入一句灵感，例如：想写一部赛博悬疑爱情，同步番茄榜热度..."
      value={chatInput}
      onChange={(e) => setChatInput(e.target.value)}
      className="rounded-2xl"
    />
    <div className="text-right mt-4">
      <Button type="primary" size="large" onClick={onCreateProject}>
        建档并进入工作台
      </Button>
    </div>
  </Card>
);
