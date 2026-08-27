import { Outlet } from "react-router-dom";
import Navbar from "./Navbar/Navbar";
import Footer from "./Footer/Footer";

const Layout = () => {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Navbar />

      <main className="mx-auto w-full max-w-screen-2xl flex-1 px-4 py-6 lg:px-8">
        <Outlet />
      </main>

      <Footer />
    </div>
  );
};

export default Layout;