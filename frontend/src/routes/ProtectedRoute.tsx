import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

interface ProtectedRouteProps {
  children: React.ReactNode;
  roles?: string[];
}

function ProtectedRoute({
  children,
  roles = [],
}: ProtectedRouteProps) {
  const { user, isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (roles.length > 0) {
    const userRole = user?.role?.toLowerCase();

    const allowedRoles = roles.map((role) =>
      role.toLowerCase()
    );

    if (!userRole || !allowedRoles.includes(userRole)) {
      return <Navigate to="/" replace />;
    }
  }

  return <>{children}</>;
}

export default ProtectedRoute;