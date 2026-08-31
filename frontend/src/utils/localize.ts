// Picking the right translation of a product / category field.
//
// The API returns every translation (`name_en` / `name_ar` / `name_fr`,
// same for `description`) and never negotiates locale — the client chooses,
// so switching language is instant with no refetch. English is the required
// base; a blank Arabic or French value falls back to it. A product name is
// never rendered blank. See
// docs/decisions/0012-product-category-translation.md.

import { SUPPORTED_LANGUAGES } from "../i18n/i18n";

type Translatable = Record<string, unknown> | null | undefined;

/**
 * The value of `base` (`"name"` | `"description"`) in `language`, falling
 * back to English, then to a legacy bare `base` key, then to "".
 */
export function localizedField(
  entity: Translatable,
  base: string,
  language?: string,
): string {
  if (!entity) return "";

  const lang = SUPPORTED_LANGUAGES.includes(language ?? "")
    ? (language as string)
    : "en";

  const inLang = entity[`${base}_${lang}`];
  if (typeof inLang === "string" && inLang.trim()) return inLang;

  const inEn = entity[`${base}_en`];
  if (typeof inEn === "string" && inEn.trim()) return inEn;

  const bare = entity[base];
  return typeof bare === "string" ? bare : "";
}

/** `localizedField(entity, "name", language)` */
export function localizedName(entity: Translatable, language?: string): string {
  return localizedField(entity, "name", language);
}

/** `localizedField(entity, "description", language)` */
export function localizedDescription(
  entity: Translatable,
  language?: string,
): string {
  return localizedField(entity, "description", language);
}

/**
 * Which of the three languages have a non-blank value for `base` — drives
 * the "filled in" indicator on the vendor / admin translation tabs.
 */
export function filledLanguages(
  values: Record<string, string | null | undefined>,
  base: string,
): string[] {
  return SUPPORTED_LANGUAGES.filter((lang) =>
    (values[`${base}_${lang}`] ?? "").trim(),
  );
}
