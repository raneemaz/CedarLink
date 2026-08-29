import { Routes, Route } from "react-router-dom";

import Layout from "./components/layout/Layout";
import ProtectedRoute from "./routes/ProtectedRoute";

import Home from "./pages/Home/Home";
import Login from "./pages/Login/Login";
import Register from "./pages/Register/Register";
import ForgotPassword from "./pages/ForgotPassword/ForgotPassword";
import ResetPassword from "./pages/ResetPassword/ResetPassword";
import RegisterVerify from "./pages/Register/RegisterVerify";
import Products from "./pages/Products/Products";
import ProductDetails from "./pages/ProductDetails/ProductDetails";
import Cart from "./pages/Cart/Cart";
import Checkout from "./pages/Checkout/Checkout";
import Orders from "./pages/Orders/Orders";
import OrderDetails from "./pages/Orders/OrderDetails";
import Profile from "./pages/Profile/Profile";
import VendorDashboard from "./pages/Vendor/VendorDashboard";
import AdminDashboard from "./pages/Admin/AdminDashboard";
import Settings from "./pages/Settings/Settings";
import SavedAddresses from "./pages/Settings/SavedAddresses";
import AddAddress from "./pages/Settings/AddAddress";
import EditAddress from "./pages/Settings/EditAddress";
import Security from "./pages/Settings/Security";
import PaymentMethods from "./pages/Settings/PaymentMethods";
import AddPaymentMethod from "./pages/Settings/AddPaymentMethod";
import EditPaymentMethod from "./pages/Settings/EditPaymentMethod";
import Language from "./pages/Settings/Language";
import Currency from "./pages/Settings/Currency";
import Notifications from "./pages/Settings/Notifications";
import ShoppingPreferences from "./pages/Settings/ShoppingPreferences";
import PrivacyData from "./pages/Settings/PrivacyData";
import NotificationsPage from "./pages/Notifications/Notifications";

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/products" element={<Products />} />
        <Route path="/products/:id" element={<ProductDetails />} />
        <Route path="/cart" element={<Cart />} />
        <Route path="/checkout" element={<Checkout />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/orders/:id" element={<OrderDetails />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/settings/addresses" element={<SavedAddresses />} />
        <Route
          path="/settings/addresses/new"
          element={<AddAddress />}
        />
        <Route
          path="/settings/addresses/:id/edit"
          element={<EditAddress />}
        />
        <Route
          path="/settings/security"
          element={<Security />}
        />
        <Route
          path="/settings/payment-methods"
          element={<PaymentMethods />}
        />
        <Route
          path="/settings/payment-methods/new"
          element={<AddPaymentMethod />}
        />
        <Route
          path="/settings/currency"
          element={<Currency />}
        />
        <Route
          path="/settings/notifications"
          element={<Notifications />}
        />
        <Route
          path="/settings/shopping"
          element={<ShoppingPreferences />}
        />
        <Route
          path="/settings/privacy"
          element={<PrivacyData />}
        />
        <Route
          path="/settings/payment-methods/:id/edit"
          element={<EditPaymentMethod />}
        />
        <Route
          path="/settings/language"
          element={<Language />}
        />
      </Route>

      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route
        path="/register/verify"
        element={<RegisterVerify />}
      />

      <Route
        path="/vendor/dashboard"
        element={
          <ProtectedRoute roles={["vendor"]}>
            <VendorDashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/admin/dashboard"
        element={
          <ProtectedRoute roles={["admin"]}>
            <AdminDashboard />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default App;