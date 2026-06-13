import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";

import HomePage from "@/pages/HomePage";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import BrowsePage from "@/pages/BrowsePage";
import ItemDetailPage from "@/pages/ItemDetailPage";
import PostItemPage from "@/pages/PostItemPage";
import DashboardPage from "@/pages/DashboardPage";
import DonatePage from "@/pages/DonatePage";
import VerifyPage from "@/pages/VerifyPage";
import PaymentSuccessPage from "@/pages/PaymentSuccessPage";
import LeaderboardPage from "@/pages/LeaderboardPage";
import HowItWorksPage from "@/pages/HowItWorksPage";
import SafetyPage from "@/pages/SafetyPage";
import AdminPage from "@/pages/AdminPage";
import ForgotPasswordPage from "@/pages/ForgotPasswordPage";
import ResetPasswordPage from "@/pages/ResetPasswordPage";
import VerifyEmailPage from "@/pages/VerifyEmailPage";
import IdentityReturnPage from "@/pages/IdentityReturnPage";
import ProfilePage from "@/pages/ProfilePage";

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/browse" element={<BrowsePage />} />
            <Route path="/items/:id" element={<ItemDetailPage />} />
            <Route path="/users/:userId" element={<ProfilePage />} />
            <Route path="/donate" element={<DonatePage />} />
            <Route path="/leaderboard" element={<LeaderboardPage />} />
            <Route path="/how-it-works" element={<HowItWorksPage />} />
            <Route path="/safety" element={<SafetyPage />} />
            <Route path="/payment-success" element={<PaymentSuccessPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/verify-email" element={<VerifyEmailPage />} />
            <Route path="/identity-return" element={<ProtectedRoute><IdentityReturnPage /></ProtectedRoute>} />
            <Route path="/admin" element={<ProtectedRoute><AdminPage /></ProtectedRoute>} />
            <Route path="/post" element={<ProtectedRoute><PostItemPage /></ProtectedRoute>} />
            <Route path="/verify" element={<ProtectedRoute><VerifyPage /></ProtectedRoute>} />
            <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          </Routes>
        </BrowserRouter>
        <Toaster position="top-center" richColors />
      </AuthProvider>
    </div>
  );
}

export default App;
