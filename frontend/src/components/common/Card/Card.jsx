function Card({ children, className = "" }) {
  return (
    <div
      className={`bg-white rounded-2xl shadow-lg p-8 ${className}`}
    >
      {children}
    </div>
  );
}

export default Card;