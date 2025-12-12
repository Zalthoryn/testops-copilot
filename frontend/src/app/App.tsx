import { Route, Routes, Navigate } from "react-router-dom";
import AppShell from "../components/common/AppShell";
import DashboardPage from "../pages/Dashboard/DashboardPage";
import TestcasesPage from "../pages/Testcases/TestcasesPage";
import AutotestsPage from "../pages/Autotests/AutotestsPage";
import StandardsPage from "../pages/Standards/StandardsPage";
import OptimizationPage from "../pages/Optimization/OptimizationPage";
import SettingsPage from "../pages/Settings/SettingsPage";
import JobDetailsPage from "../pages/Jobs/JobDetailsPage";

const App = () => {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/testcases" element={<TestcasesPage />} />
        <Route path="/autotests" element={<AutotestsPage />} />
        <Route path="/standards" element={<StandardsPage />} />
        <Route path="/optimization" element={<OptimizationPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/jobs/:jobId" element={<JobDetailsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
};

export default App;

