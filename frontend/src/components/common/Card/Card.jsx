function Card({ children, className = "" }) {
  return (
    <div
      className={`bg-paper-raised rounded-2xl shadow-lg p-8 ${className}`}
    >
      {children}
    </div>
  );
}

export default Card;