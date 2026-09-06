import { createBrowserRouter } from "react-router-dom";

import { AdminRoute, ProtectedRoute } from "./auth/ProtectedRoute";
import { AdminLayout } from "./layouts/AdminLayout";
import { DashboardLayout } from "./layouts/DashboardLayout";
import { PublicLayout } from "./layouts/PublicLayout";
import { AnnouncementsAdminPage } from "./pages/admin/AnnouncementsAdminPage";
import { CouponsAdminPage } from "./pages/admin/CouponsAdminPage";
import { DashboardPage as AdminDashboardPage } from "./pages/admin/DashboardPage";
import { ReportsAdminPage } from "./pages/admin/ReportsAdminPage";
import { LedgerAdminPage } from "./pages/admin/LedgerAdminPage";
import { OrdersAdminPage } from "./pages/admin/OrdersAdminPage";
import { PricingRulesAdminPage } from "./pages/admin/PricingRulesAdminPage";
import { ProvidersAdminPage } from "./pages/admin/ProvidersAdminPage";
import { ServicesAdminPage } from "./pages/admin/ServicesAdminPage";
import { SettingsAdminPage } from "./pages/admin/SettingsAdminPage";
import { TicketsAdminPage } from "./pages/admin/TicketsAdminPage";
import { UsersAdminPage } from "./pages/admin/UsersAdminPage";
import { AddFundsPage } from "./pages/dashboard/AddFundsPage";
import { AffiliatePage } from "./pages/dashboard/AffiliatePage";
import { ApiPage } from "./pages/dashboard/ApiPage";
import { BulkOrderPage } from "./pages/dashboard/BulkOrderPage";
import { DashboardHome } from "./pages/dashboard/DashboardHome";
import { NewOrderPage } from "./pages/dashboard/NewOrderPage";
import { OrderHistoryPage } from "./pages/dashboard/OrderHistoryPage";
import { ServicesListPage } from "./pages/dashboard/ServicesListPage";
import { SettingsPage } from "./pages/dashboard/SettingsPage";
import { TicketsPage } from "./pages/dashboard/TicketsPage";
import { ApiDocsPage } from "./pages/public/ApiDocsPage";
import { ForgotPasswordPage } from "./pages/public/ForgotPasswordPage";
import { HomePage } from "./pages/public/HomePage";
import { LoginPage } from "./pages/public/LoginPage";
import { PricingPage } from "./pages/public/PricingPage";
import { RegisterPage } from "./pages/public/RegisterPage";
import { ResetPasswordPage } from "./pages/public/ResetPasswordPage";
import { ServiceHealthPage } from "./pages/public/ServiceHealthPage";
import { VerifyEmailPage } from "./pages/public/VerifyEmailPage";

export const router = createBrowserRouter([
  {
    element: <PublicLayout />,
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/services", element: <ServicesListPage /> },
      { path: "/pricing", element: <PricingPage /> },
      { path: "/service-health", element: <ServiceHealthPage /> },
      { path: "/api-docs", element: <ApiDocsPage /> },
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
      { path: "/verify-email", element: <VerifyEmailPage /> },
      { path: "/forgot-password", element: <ForgotPasswordPage /> },
      { path: "/reset-password", element: <ResetPasswordPage /> },
    ],
  },
  {
    path: "/dashboard",
    element: (
      <ProtectedRoute>
        <DashboardLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <DashboardHome /> },
      { path: "new-order", element: <NewOrderPage /> },
      { path: "services", element: <ServicesListPage /> },
      { path: "bulk-order", element: <BulkOrderPage /> },
      { path: "orders", element: <OrderHistoryPage /> },
      { path: "add-funds", element: <AddFundsPage /> },
      { path: "api", element: <ApiPage /> },
      { path: "tickets", element: <TicketsPage /> },
      { path: "affiliate", element: <AffiliatePage /> },
      { path: "settings", element: <SettingsPage /> },
    ],
  },
  {
    path: "/admin",
    element: (
      <AdminRoute>
        <AdminLayout />
      </AdminRoute>
    ),
    children: [
      { index: true, element: <AdminDashboardPage /> },
      { path: "users", element: <UsersAdminPage /> },
      { path: "services", element: <ServicesAdminPage /> },
      { path: "pricing-rules", element: <PricingRulesAdminPage /> },
      { path: "providers", element: <ProvidersAdminPage /> },
      { path: "orders", element: <OrdersAdminPage /> },
      { path: "ledger", element: <LedgerAdminPage /> },
      { path: "tickets", element: <TicketsAdminPage /> },
      { path: "reports", element: <ReportsAdminPage /> },
      { path: "coupons", element: <CouponsAdminPage /> },
      { path: "announcements", element: <AnnouncementsAdminPage /> },
      { path: "settings", element: <SettingsAdminPage /> },
    ],
  },
]);
