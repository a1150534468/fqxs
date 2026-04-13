
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

interface AuthRouteProps {
  children: React.ReactNode;
}

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
}

export const AuthRoute: React.FC<AuthRouteProps> = ({ children }) => {
  const token = useAuthStore((state) => state.token);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const location = useLocation();

  if (!token || isTokenExpired(token)) {
    if (token) clearAuth();
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};
