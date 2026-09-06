export default function Footer() {
  return (
    <footer className="border-t border-line bg-paper-raised">
      <div className="mx-auto max-w-7xl px-4 py-6 text-small text-ink-muted">
        © {new Date().getFullYear()} CedarLink
      </div>
    </footer>
  );
}