import { Navigate, Route, Routes } from "react-router-dom";

import AppLayout from "./layouts/AppLayout.jsx";
import ProtectedRoute from "./routes/ProtectedRoute.jsx";
import PublicOnlyRoute from "./routes/PublicOnlyRoute.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import ClassDetailsPage from "./pages/ClassDetailsPage.jsx";
import ClassCoursesPage from "./pages/ClassCoursesPage.jsx";
import CourseCataloguePage from "./pages/CourseCataloguePage.jsx";
import CreateClassPage from "./pages/CreateClassPage.jsx";
import JoinClassPage from "./pages/JoinClassPage.jsx";
import MyCoursesPage from "./pages/MyCoursesPage.jsx";
import MyClassesPage from "./pages/MyClassesPage.jsx";

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/classes" element={<MyClassesPage />} />
          <Route path="/classes/new" element={<CreateClassPage />} />
          <Route path="/classes/join" element={<JoinClassPage />} />
          <Route path="/classes/:classId" element={<ClassDetailsPage />} />
          <Route path="/classes/:classId/courses" element={<ClassCoursesPage />} />
          <Route path="/classes/:classId/my-courses" element={<MyCoursesPage />} />
          <Route path="/courses" element={<CourseCataloguePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}

export default App;
