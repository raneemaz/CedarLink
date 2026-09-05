function Card({ children, className = "" }) {
  return (
    <div
      className={`bg-surface-raised rounded-2xl shadow-lg p-8 ${className}`}
    >
      {children}
    </div>
  );
}

export default Card;