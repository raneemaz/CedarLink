export default function Footer() {
  return (
    <footer className="border-t border-border bg-surface-raised">
      <div className="mx-auto max-w-7xl px-4 py-6 text-sm text-text-muted">
        © {new Date().getFullYear()} CedarLink
      </div>
    </footer>
  );
}