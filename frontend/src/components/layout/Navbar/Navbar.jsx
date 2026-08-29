import { useEffect, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../../context/AuthContext";
import api from "../../../services/api";
import logo from "../../../assets/Logoo.png";

import { Search, ShoppingCart, User, Menu } from "lucide-react";
import NotificationBell from "../../notifications/NotificationBell";

const Navbar = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [cartCount, setCartCount] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");

  const handleSearchSubmit = (event) => {
    event.preventDefault();
    const query = searchQuery.trim();
    navigate(query ? `/products?keyword=${encodeURIComponent(query)}` : "/products");
  };

  useEffect(() => {
    const fetchCartCount = async () => {
      if (!isAuthenticated) {
        setCartCount(0);
        return;
      }

      try {
        const response = await api.get("/cart");

        const stores = response.data.stores || [];

        const totalQuantity = stores.reduce((total, store) => {
          const storeQuantity = (store.items || []).reduce(
            (sum, item) => sum + item.quantity,
            0,
          );

          return total + storeQuantity;
        }, 0);

        setCartCount(totalQuantity);
      } catch (error) {
        console.error("Failed to fetch cart:", error);
        setCartCount(0);
      }
    };

    fetchCartCount();

    window.addEventListener("cartUpdated", fetchCartCount);

    return () => {
      window.removeEventListener("cartUpdated", fetchCartCount);
    };
  }, [isAuthenticated]);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <nav className="sticky top-0 z-50 border-b border-slate-200 bg-white shadow-sm">
      <div className="mx-auto flex h-20 max-w-screen-2xl items-center justify-between px-4 lg:px-8">
        {/* Logo */}
        <div className="mb-1 flex items-center justify-center gap-2">
          <img
            src={logo}
            alt={t("navbar.logoAlt")}
            className="h-10 w-auto object-contain"
          />

          <Link to="/" className="text-xl font-bold text-emerald-700">
            CedarLink
          </Link>
        </div>

        {/* Navigation */}
        <div className="hidden items-center gap-8 text-sm font-medium lg:flex">
          <NavLink
            to="/"
            className={({ isActive }) =>
              isActive
                ? "text-emerald-700"
                : "text-slate-700 hover:text-emerald-700"
            }
          >
            {t("navbar.home")}
          </NavLink>

          <NavLink
            to="/products"
            className={({ isActive }) =>
              isActive
                ? "text-emerald-700"
                : "text-slate-700 hover:text-emerald-700"
            }
          >
            {t("navbar.products")}
          </NavLink>

          <NavLink
            to="/categories"
            className="text-slate-700 hover:text-emerald-700"
          >
            {t("navbar.categories")}
          </NavLink>

          <NavLink
            to="/stores"
            className="text-slate-700 hover:text-emerald-700"
          >
            {t("navbar.stores")}
          </NavLink>
        </div>

        {/* Search */}
        <form
          onSubmit={handleSearchSubmit}
          className="mx-8 hidden w-full max-w-md xl:flex"
        >
          <div className="flex w-full items-center rounded-full border border-slate-300 bg-slate-50 px-4">
            <Search size={18} className="text-slate-400" />

            <input
              type="text"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder={t("navbar.search")}
              className="w-full bg-transparent px-3 py-2 outline-none"
            />
          </div>
        </form>

        {/* Right */}
        <div className="flex items-center gap-5">
          <Link
            to="/cart"
            aria-label={t("navbar.cart")}
            className="relative cursor-pointer hover:text-emerald-700"
          >
            <ShoppingCart size={24} />

            <span className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-emerald-700 text-xs text-white">
              {cartCount}
            </span>
          </Link>

          {!isAuthenticated ? (
            <div className="flex items-center gap-3">
              <Link
                to="/login"
                className="rounded-lg border border-emerald-700 px-4 py-2 font-medium text-emerald-700 transition hover:bg-emerald-50"
              >
                {t("navbar.login")}
              </Link>

              <Link
                to="/register"
                className="rounded-lg bg-emerald-700 px-4 py-2 font-medium text-white transition hover:bg-emerald-800"
              >
                {t("navbar.register")}
              </Link>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <NotificationBell />

              <div className="group relative">
                <button
                  type="button"
                  className="flex items-center gap-2 rounded-lg px-3 py-2 transition hover:bg-slate-100"
                >
                  <User size={20} />

                  <span className="cursor-pointer font-medium">
                    {user?.username ||
                      user?.name ||
                      t("navbar.profile")}
                  </span>
                </button>

                {/* Profile Dropdown */}
                <div className="absolute right-0 top-full mt-1 hidden w-48 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg group-hover:block">
                  <Link
                    to="/profile"
                    className="block cursor-pointer px-4 py-3 text-sm text-slate-700 transition hover:bg-slate-100 hover:text-emerald-700"
                  >
                    {t("navbar.myProfile")}
                  </Link>

                  <Link
                    to="/settings"
                    className="block cursor-pointer px-4 py-3 text-sm text-slate-700 transition hover:bg-slate-100 hover:text-emerald-700"
                  >
                    {t("navbar.settings")}
                  </Link>
                </div>
              </div>

              <button
                type="button"
                onClick={handleLogout}
                className="cursor-pointer rounded-lg bg-red-500 px-4 py-2 text-white transition hover:bg-red-600"
              >
                {t("navbar.logout")}
              </button>
            </div>
          )}

          <button
            type="button"
            aria-label={t("navbar.menu")}
            className="lg:hidden"
          >
            <Menu size={28} />
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;