import { Routes, Route, Navigate } from "react-router-dom";

import Layout from "./components/layout/Layout";
import VendorLayout from "./components/layout/VendorLayout";
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
import VendorStore from "./pages/Vendor/VendorStore";
import VendorProducts from "./pages/Vendor/VendorProducts";
import VendorProductForm from "./pages/Vendor/VendorProductForm";
import VendorOrders from "./pages/Vendor/VendorOrders";
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
import NotificationPreferences from "./pages/Settings/NotificationPreferences";
import ShoppingPreferences from "./pages/Settings/ShoppingPreferences";
import PrivacyData from "./pages/Settings/PrivacyData";
import NotificationsFeed from "./pages/Notifications/NotificationsFeed";
import NotFound from "./pages/NotFound/NotFound";

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
        <Route path="/notifications" element={<NotificationsFeed />} />
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
          element={<NotificationPreferences />}
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

        <Route path="*" element={<NotFound />} />
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
        path="/vendor"
        element={
          <ProtectedRoute roles={["vendor"]}>
            <VendorLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="store" replace />} />
        <Route path="store" element={<VendorStore />} />
        <Route path="products" element={<VendorProducts />} />
        <Route path="products/new" element={<VendorProductForm />} />
        <Route
          path="products/:id/edit"
          element={<VendorProductForm />}
        />
        <Route path="orders" element={<VendorOrders />} />
        <Route path="*" element={<NotFound />} />
      </Route>

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