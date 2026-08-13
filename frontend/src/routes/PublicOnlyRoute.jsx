import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "../auth/useAuth.js";
import LoadingScreen from "../components/LoadingScreen.jsx";

function PublicOnlyRoute() {
  const { isAuthenticated, status } = useAuth();

  if (status === "checking") {
    return <LoadingScreen message="Checking your session..." />;
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}

export default PublicOnlyRoute;
