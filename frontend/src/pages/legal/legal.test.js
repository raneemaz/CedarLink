/**
 * The Privacy Policy and Terms pages are static translated documents. Two
 * things are worth a test and neither needs a DOM:
 *
 *  1. The "last updated" date is one real date, driven by the constant.
 *  2. Every section and control the components render has a string in all
 *     three locales — a missing translation would ship as a visible key.
 *
 * `node --test`, no dependency. The component section lists are read as
 * text rather than imported, so this file stays plain JS.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { LEGAL_LAST_UPDATED, LEGAL_LAST_UPDATED_ISO } from "./legalMeta.js";

const HERE = new URL(".", import.meta.url).pathname.replace(/^\/(\w:)/, "$1");

function load(locale) {
  return JSON.parse(
    readFileSync(`${HERE}../../i18n/${locale}.json`, "utf-8"),
  );
}

function arrayLiteral(source, name) {
  const match = source.match(
    new RegExp(`const ${name} = \\[([\\s\\S]*?)\\];`),
  );
  assert.ok(match, `${name} array not found`);
  return [...match[1].matchAll(/"([a-zA-Z]+)"/g)].map((m) => m[1]);
}

const LOCALES = ["en", "ar", "fr"];
const resources = Object.fromEntries(LOCALES.map((l) => [l, load(l)]));

test("last updated is a single real calendar date", () => {
  assert.match(LEGAL_LAST_UPDATED, /^\d{4}-\d{2}-\d{2}$/);

  const parsed = new Date(LEGAL_LAST_UPDATED_ISO);
  assert.ok(Number.isFinite(parsed.getTime()));
  assert.equal(parsed.toISOString().slice(0, 10), LEGAL_LAST_UPDATED);
});

test("privacy policy: every section is translated in all three locales", () => {
  const sections = arrayLiteral(
    readFileSync(`${HERE}PrivacyPolicy.jsx`, "utf-8"),
    "SECTIONS",
  );
  assert.ok(sections.includes("contact"));

  for (const locale of LOCALES) {
    for (const key of sections) {
      const section = resources[locale].privacyPolicy.sections[key];
      assert.ok(section?.title, `${locale} privacyPolicy.${key}.title`);
      assert.ok(section?.body, `${locale} privacyPolicy.${key}.body`);
    }
  }
});

test("privacy policy: every linked control is translated", () => {
  const controls = [...readFileSync(`${HERE}PrivacyPolicy.jsx`, "utf-8")
    .matchAll(/key: "([a-zA-Z]+)" \}/g)].map((m) => m[1]);
  assert.ok(controls.length >= 5);

  for (const locale of LOCALES) {
    for (const key of controls) {
      assert.ok(
        resources[locale].privacyPolicy.controls[key],
        `${locale} privacyPolicy.controls.${key}`,
      );
    }
  }
});

test("terms: every section is translated in all three locales", () => {
  const sections = arrayLiteral(
    readFileSync(`${HERE}Terms.jsx`, "utf-8"),
    "SECTIONS",
  );

  for (const locale of LOCALES) {
    for (const key of sections) {
      const section = resources[locale].terms.sections[key];
      assert.ok(section?.title, `${locale} terms.${key}.title`);
      assert.ok(section?.body, `${locale} terms.${key}.body`);
    }
  }
});

test("footer links are translated in all three locales", () => {
  for (const locale of LOCALES) {
    assert.ok(resources[locale].footer.privacy);
    assert.ok(resources[locale].footer.terms);
  }
});

test("the agree-to-terms line keeps its link tags in every locale", () => {
  for (const locale of LOCALES) {
    const line = resources[locale].register.agreeToTerms;
    assert.match(line, /<terms>.*<\/terms>/);
    assert.match(line, /<privacy>.*<\/privacy>/);
  }
});
