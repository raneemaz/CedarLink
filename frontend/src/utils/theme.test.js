/**
 * Theme resolution.
 *
 * Node's own test runner, no dependency added: `node --test`. The logic
 * worth testing here has no DOM and no React in it, which is why it was
 * pulled out of the provider in the first place.
 */
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  DEFAULT_THEME,
  applyTheme,
  effectiveTheme,
  normalizeTheme,
  readThemeCache,
  themeAttribute,
  writeThemeCache,
} from "./theme.js";

/** The two DOM methods applyTheme touches, and nothing else. */
function fakeRoot() {
  const attrs = new Map();
  return {
    attrs,
    setAttribute: (k, v) => attrs.set(k, v),
    removeAttribute: (k) => attrs.delete(k),
  };
}

function fakeStorage(initial) {
  const map = new Map(Object.entries(initial || {}));
  return {
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => map.set(k, v),
    map,
  };
}

test("system is the default, and anything unrecognised falls back to it", () => {
  assert.equal(DEFAULT_THEME, "system");
  assert.equal(normalizeTheme(undefined), "system");
  assert.equal(normalizeTheme(null), "system");
  assert.equal(normalizeTheme(""), "system");
  assert.equal(normalizeTheme("solarized"), "system");
  assert.equal(normalizeTheme("Dark"), "system"); // case matters
});

test("an explicit choice is kept", () => {
  assert.equal(normalizeTheme("light"), "light");
  assert.equal(normalizeTheme("dark"), "dark");
  assert.equal(normalizeTheme("system"), "system");
});

test("system sets no attribute, so CSS keeps following the device", () => {
  // The important half: if `system` resolved to a concrete attribute, a
  // device that switched to dark while the page was open would be stuck.
  assert.equal(themeAttribute("system"), null);
  assert.equal(themeAttribute("light"), "light");
  assert.equal(themeAttribute("dark"), "dark");
});

test("an explicit light choice beats a device set to dark", () => {
  // The whole reason the media query in index.css is guarded with
  // :not([data-theme="light"]).
  assert.equal(themeAttribute("light"), "light");
  assert.equal(effectiveTheme("light", true), "light");

  const root = fakeRoot();
  applyTheme("light", root);
  assert.equal(root.attrs.get("data-theme"), "light");
});

test("an explicit dark choice beats a device set to light", () => {
  assert.equal(effectiveTheme("dark", false), "dark");

  const root = fakeRoot();
  applyTheme("dark", root);
  assert.equal(root.attrs.get("data-theme"), "dark");
});

test("system follows the device in both directions", () => {
  assert.equal(effectiveTheme("system", true), "dark");
  assert.equal(effectiveTheme("system", false), "light");
});

test("switching to system removes the attribute rather than setting one", () => {
  const root = fakeRoot();

  applyTheme("dark", root);
  assert.equal(root.attrs.get("data-theme"), "dark");

  applyTheme("system", root);
  assert.equal(root.attrs.has("data-theme"), false);
});

test("the cache round-trips, and a corrupt value is not trusted", () => {
  const store = fakeStorage();

  writeThemeCache("dark", store);
  assert.equal(readThemeCache(store), "dark");

  store.map.set("cedarlink_theme", "chartreuse");
  assert.equal(readThemeCache(store), "system");

  assert.equal(readThemeCache(fakeStorage()), "system");
});

test("storage that throws does not take the page down with it", () => {
  const hostile = {
    getItem() {
      throw new Error("blocked");
    },
    setItem() {
      throw new Error("blocked");
    },
  };

  assert.equal(readThemeCache(hostile), "system");
  assert.doesNotThrow(() => writeThemeCache("dark", hostile));
});

test("the pre-paint script in index.html agrees with applyTheme", async () => {
  // The inline script is a hand-written copy of `themeAttribute` that has
  // to run before the bundle loads. If the two ever disagree, a
  // dark-theme user gets a white flash — so the rule is asserted here
  // against the actual file rather than trusted to stay in step.
  const { readFileSync } = await import("node:fs");
  const html = readFileSync(
    new URL("../../index.html", import.meta.url),
    "utf8",
  );

  assert.match(html, /cedarlink_theme/);
  assert.match(html, /setAttribute\("data-theme", theme\)/);
  assert.match(html, /removeAttribute\("data-theme"\)/);
  // It must only ever stamp an explicit choice.
  assert.match(html, /theme === "light" \|\| theme === "dark"/);
});
