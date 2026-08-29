import { Link } from "react-router-dom";

function NotFound() {
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center px-6 text-center">
      <p className="text-5xl font-bold text-emerald-700">404</p>
      <h1 className="mt-4 text-2xl font-semibold text-gray-900">
        Page not found
      </h1>
      <p className="mt-2 text-gray-500">
        The page you are looking for doesn&apos;t exist or has moved.
      </p>
      <Link
        to="/"
        className="mt-6 rounded-lg bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-800"
      >
        Back to home
      </Link>
    </div>
  );
}

export default NotFound;
