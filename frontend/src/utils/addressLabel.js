// The address label is stored as the canonical English value the form's
// select produced ("Home" / "Work" / "Other"), so it needs translating for
// display. Anything else — an older row, or a value from outside the form —
// is shown as the customer typed it rather than dropped.
//
// NOTE: pages/Settings/SavedAddresses.jsx still renders address.label raw.
// Left alone here to keep this change to its own scope; worth switching it
// to this helper next time that page is touched.

const KNOWN = {
  Home: "addresses.labelHome",
  Work: "addresses.labelWork",
  Other: "addresses.labelOther",
};

/** Display name for a saved address label. `t` is i18next's translator. */
export function addressLabel(t, label) {
  const raw = String(label || "").trim();
  const key = KNOWN[raw];
  return key ? t(key) : raw;
}
