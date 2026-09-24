import { Navigate, useParams, useSearchParams } from "react-router-dom";

import ClassOverviewPage from "./ClassOverviewPage.jsx";

// Module 7 action URLs use the backend's class overview tab convention.
// Preserve those URLs on links, then route the matching tab inside the SPA.
function ClassEntryPage() {
  const { classId } = useParams();
  const [searchParams] = useSearchParams();
  const tab = searchParams.get("tab");
  if (tab === "announcements" || tab === "resources") {
    const resource = tab === "resources" ? searchParams.get("resource") : null;
    const query = resource ? `?resource=${encodeURIComponent(resource)}` : "";
    return <Navigate replace to={`/classes/${classId}/${tab}${query}`} />;
  }
  return <ClassOverviewPage />;
}

export default ClassEntryPage;
