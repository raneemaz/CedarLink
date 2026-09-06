import { useEffect, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../../context/AuthContext";
import api from "../../../services/api";

import { Search, ShoppingCart, User, Menu, X } from "lucide-react";
import NotificationBell from "../../notifications/NotificationBell";

const NAV_LINKS = [
  { to: "/", key: "home" },
  { to: "/products", key: "products" },
  { to: "/categories", key: "categories" },
  { to: "/stores", key: "stores" },
];

const Navbar = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [cartCount, setCartCount] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);

  // Role-aware console links.
  const roleLinks = [];
  if (user?.role === "vendor") {
    roleLinks.push({ to: "/vendor/store", label: t("navbar.myStore") });
  }
  if (user?.role === "admin") {
    roleLinks.push({ to: "/admin", label: t("navbar.admin") });
  }

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
    setMobileOpen(false);
    navigate("/");
  };

  return (
    <nav className="sticky top-0 z-50 border-b border-line bg-paper-raised shadow-card">
      <div className="mx-auto flex h-20 max-w-screen-2xl items-center justify-between px-4 lg:px-8">
        {/* Logo */}
        <div className="mb-1 flex items-center justify-center gap-2">
          {/* alt="" on purpose: the wordmark is right there, and a
              screen reader announcing "CedarLink CedarLink" is worse
              than silence. The link's accessible name is its text.
              Explicit width/height so the header does not shift while
              the mark loads — the source is 158x176, portrait. */}
          <img
            src="/cedarlink-logo.png"
            alt=""
            width={32}
            height={36}
            className="h-9 w-auto object-contain"
          />

          <Link
            to="/"
            className="font-display text-wordmark font-semibold text-cedar-strong"
          >
            CedarLink
          </Link>
        </div>

        {/* Navigation */}
        <div className="hidden items-center gap-8 text-small font-medium lg:flex">
          <NavLink
            to="/"
            className={({ isActive }) =>
              isActive
                ? "text-cedar"
                : "text-ink-body hover:text-cedar"
            }
          >
            {t("navbar.home")}
          </NavLink>

          <NavLink
            to="/products"
            className={({ isActive }) =>
              isActive
                ? "text-cedar"
                : "text-ink-body hover:text-cedar"
            }
          >
            {t("navbar.products")}
          </NavLink>

          <NavLink
            to="/categories"
            className="text-ink-body hover:text-cedar"
          >
            {t("navbar.categories")}
          </NavLink>

          <NavLink
            to="/stores"
            className="text-ink-body hover:text-cedar"
          >
            {t("navbar.stores")}
          </NavLink>
        </div>

        {/* Search */}
        <form
          onSubmit={handleSearchSubmit}
          className="mx-8 hidden w-full max-w-md xl:flex"
        >
          <div className="flex w-full items-center rounded-pill border border-line-strong bg-paper px-4">
            <Search size={18} className="text-ink-faint" />

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
            className="relative cursor-pointer hover:text-cedar"
          >
            <ShoppingCart size={24} />

            <span className="absolute -end-2 -top-2 flex h-5 w-5 items-center justify-center rounded-pill bg-cedar text-micro text-on-cedar">
              {cartCount}
            </span>
          </Link>

          {!isAuthenticated ? (
            <div className="hidden items-center gap-3 lg:flex">
              <Link
                to="/login"
                className="rounded-control border border-cedar px-4 py-2 font-medium text-cedar transition hover:bg-cedar-subtle"
              >
                {t("navbar.login")}
              </Link>

              <Link
                to="/register"
                className="rounded-control bg-cedar px-4 py-2 font-medium text-on-cedar transition hover:bg-cedar-strong"
              >
                {t("navbar.register")}
              </Link>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <NotificationBell />

              {/* Text actions live in the mobile drawer below lg. */}
              <div className="group relative hidden lg:block">
                <button
                  type="button"
                  className="flex items-center gap-2 rounded-control px-3 py-2 transition hover:bg-paper-sunken"
                >
                  <User size={20} />

                  <span className="cursor-pointer font-medium">
                    {user?.username ||
                      user?.name ||
                      t("navbar.profile")}
                  </span>
                </button>

                {/* Profile Dropdown */}
                <div className="absolute end-0 top-full mt-1 hidden w-48 overflow-hidden rounded-control border border-line bg-paper-raised shadow-lift group-hover:block">
                  {roleLinks.map((link) => (
                    <Link
                      key={link.to}
                      to={link.to}
                      className="block cursor-pointer px-4 py-3 text-small font-medium text-cedar transition hover:bg-paper-sunken"
                    >
                      {link.label}
                    </Link>
                  ))}

                  <Link
                    to="/profile"
                    className="block cursor-pointer px-4 py-3 text-small text-ink-body transition hover:bg-paper-sunken hover:text-cedar"
                  >
                    {t("navbar.myProfile")}
                  </Link>

                  <Link
                    to="/settings"
                    className="block cursor-pointer px-4 py-3 text-small text-ink-body transition hover:bg-paper-sunken hover:text-cedar"
                  >
                    {t("navbar.settings")}
                  </Link>
                </div>
              </div>

              <button
                type="button"
                onClick={handleLogout}
                className="hidden cursor-pointer rounded-control bg-danger-accent px-4 py-2 text-on-danger transition hover:bg-danger lg:block"
              >
                {t("navbar.logout")}
              </button>
            </div>
          )}

          <button
            type="button"
            aria-label={t("navbar.menu")}
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen((open) => !open)}
            className="lg:hidden"
          >
            {mobileOpen ? <X size={28} /> : <Menu size={28} />}
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="border-t border-line bg-paper-raised px-4 py-3 lg:hidden">
          <nav className="flex flex-col">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === "/"}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `rounded-control px-3 py-2.5 text-small font-medium ${
                    isActive
                      ? "bg-cedar-subtle text-cedar"
                      : "text-ink-body hover:bg-paper-sunken"
                  }`
                }
              >
                {t(`navbar.${link.key}`)}
              </NavLink>
            ))}

            <div className="my-2 border-t border-line-subtle" />

            {isAuthenticated ? (
              <>
                {roleLinks.map((link) => (
                  <Link
                    key={link.to}
                    to={link.to}
                    onClick={() => setMobileOpen(false)}
                    className="rounded-control px-3 py-2.5 text-small font-medium text-cedar hover:bg-paper-sunken"
                  >
                    {link.label}
                  </Link>
                ))}
                <Link
                  to="/profile"
                  onClick={() => setMobileOpen(false)}
                  className="rounded-control px-3 py-2.5 text-small text-ink-body hover:bg-paper-sunken"
                >
                  {t("navbar.myProfile")}
                </Link>
                <Link
                  to="/settings"
                  onClick={() => setMobileOpen(false)}
                  className="rounded-control px-3 py-2.5 text-small text-ink-body hover:bg-paper-sunken"
                >
                  {t("navbar.settings")}
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="mt-1 rounded-control px-3 py-2.5 text-start text-small font-medium text-danger hover:bg-danger-subtle"
                >
                  {t("navbar.logout")}
                </button>
              </>
            ) : (
              <div className="flex gap-3 px-3 py-2">
                <Link
                  to="/login"
                  onClick={() => setMobileOpen(false)}
                  className="flex-1 rounded-control border border-cedar px-4 py-2 text-center font-medium text-cedar"
                >
                  {t("navbar.login")}
                </Link>
                <Link
                  to="/register"
                  onClick={() => setMobileOpen(false)}
                  className="flex-1 rounded-control bg-cedar px-4 py-2 text-center font-medium text-on-cedar"
                >
                  {t("navbar.register")}
                </Link>
              </div>
            )}
          </nav>
        </div>
      )}
    </nav>
  );
};

export default Navbar;