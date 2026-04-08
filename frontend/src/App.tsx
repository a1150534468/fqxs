
import { Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { MainLayout } from './components/MainLayout';
import { AuthRoute } from './components/AuthRoute';
import Login from './pages/Login';
import Inspirations from './pages/Inspirations';
import Novels from './pages/Novels';
import Dashboard from './pages/Dashboard';
import LLMProviders from './pages/LLMProviders';
import { Chapters } from './pages/Chapters';
import { ChapterEditor } from './pages/Chapters/ChapterEditor';
import { ChapterPreview } from './pages/Chapters/ChapterPreview';
import './App.css';

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route path="/" element={
          <AuthRoute>
            <MainLayout />
          </AuthRoute>
        }>
          <Route index element={<Dashboard />} />
          <Route path="inspirations" element={<Inspirations />} />
          <Route path="novels" element={<Novels />} />
          <Route path="novels/:projectId/chapters" element={<Chapters />} />
          <Route path="novels/:projectId/chapters/create" element={<ChapterEditor />} />
          <Route path="novels/:projectId/chapters/:chapterId/edit" element={<ChapterEditor />} />
          <Route path="novels/:projectId/chapters/:chapterId/preview" element={<ChapterPreview />} />
          <Route path="llm-providers" element={<LLMProviders />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ConfigProvider>
  );
}

export default App;
