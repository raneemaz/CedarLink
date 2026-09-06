function Card({ children, className = "" }) {
  return (
    <div
      className={`bg-paper-raised rounded-card shadow-lift p-8 ${className}`}
    >
      {children}
    </div>
  );
}

export default Card;