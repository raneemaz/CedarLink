import LegalDocument from "./LegalDocument";

const SECTIONS = [
  "marketplace",
  "accounts",
  "customer",
  "vendor",
  "orders",
  "payment",
  "cancellation",
  "coupons",
  "delivery",
  "reviews",
  "suspension",
  "availability",
  "liability",
  "governing",
  "changes",
  "contact",
];

export default function Terms() {
  return <LegalDocument ns="terms" sectionKeys={SECTIONS} />;
}
