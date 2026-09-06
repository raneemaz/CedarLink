import LegalDocument from "./LegalDocument";

// Order is the reading order of the page. "contact" stays last: the shared
// shell renders the linked account controls directly after it.
const SECTIONS = [
  "law",
  "identity",
  "addresses",
  "orders",
  "payment",
  "reviews",
  "preferences",
  "security",
  "technical",
  "sharing",
  "deletion",
  "childrens",
  "changes",
  "contact",
];

// The working controls the policy text points at. Access and correction
// live in the account pages; deletion lives on the privacy page. There is
// no export control yet, so the policy does not link one.
const CONTROLS = [
  { to: "/profile", key: "profile" },
  { to: "/settings/addresses", key: "addresses" },
  { to: "/settings/payment-methods", key: "payment" },
  { to: "/settings/notifications", key: "notifications" },
  { to: "/settings/security", key: "security" },
  { to: "/settings/privacy", key: "privacy" },
];

export default function PrivacyPolicy() {
  return (
    <LegalDocument
      ns="privacyPolicy"
      sectionKeys={SECTIONS}
      controls={CONTROLS}
    />
  );
}
