import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

/**
 * "Back to X" navigation link. The arrow is an icon, not a glyph, so it
 * mirrors in RTL (points right in Arabic). Pass `to` for a route link or
 * `onClick` for an in-page handler.
 */
export default function BackLink({ to, onClick, children, className = "" }) {
  const classes = [
    "inline-flex items-center gap-1.5 text-sm font-medium",
    "text-emerald-700 hover:underline",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  const body = (
    <>
      <ArrowLeft size={16} aria-hidden="true" className="rtl:rotate-180" />
      <span>{children}</span>
    </>
  );

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={classes}>
        {body}
      </button>
    );
  }

  return (
    <Link to={to} className={classes}>
      {body}
    </Link>
  );
}
