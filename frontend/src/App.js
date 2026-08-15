import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Customers from "@/pages/Customers";
import Masters from "@/pages/Masters";
import Jobs from "@/pages/Jobs";
import JobDetail from "@/pages/JobDetail";
import NewJob from "@/pages/NewJob";
import Users from "@/pages/Users";
import Audit from "@/pages/Audit";
import Verify from "@/pages/Verify";

function Protected({ children }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading || user === null)
    return <div className="min-h-screen grid place-items-center text-slate-500">Loading…</div>;
  if (!user) return <Navigate to="/login" state={{ from: loc }} replace />;
  return <Layout>{children}</Layout>;
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Toaster position="top-right" richColors />
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/verify/:vid" element={<Verify />} />
            <Route path="/" element={<Protected><Dashboard /></Protected>} />
            <Route path="/customers" element={<Protected><Customers /></Protected>} />
            <Route path="/masters" element={<Protected><Masters /></Protected>} />
            <Route path="/jobs" element={<Protected><Jobs /></Protected>} />
            <Route path="/jobs/new" element={<Protected><NewJob /></Protected>} />
            <Route path="/jobs/:id" element={<Protected><JobDetail /></Protected>} />
            <Route path="/users" element={<Protected><Users /></Protected>} />
            <Route path="/audit" element={<Protected><Audit /></Protected>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
