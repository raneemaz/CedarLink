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
  themeCacheKey,
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

  writeThemeCache("dark", null, store);
  assert.equal(readThemeCache(null, store), "dark");

  store.map.set("cedarlink_theme", "chartreuse");
  assert.equal(readThemeCache(null, store), "system");

  assert.equal(readThemeCache(null, fakeStorage()), "system");
});

test("two accounts on one browser do not share a cached theme", () => {
  // The shared-browser case the pre-paint script would otherwise paint
  // wrong: user 1 chooses dark, user 2 signs in on the same machine and
  // must not get a frame of user 1's theme.
  const store = fakeStorage();

  writeThemeCache("dark", 1, store);
  writeThemeCache("light", 2, store);

  assert.equal(readThemeCache(1, store), "dark");
  assert.equal(readThemeCache(2, store), "light");

  // And neither of them is the signed-out entry.
  assert.equal(readThemeCache(null, store), "system");

  assert.equal(themeCacheKey(null), "cedarlink_theme");
  assert.equal(themeCacheKey(1), "cedarlink_theme:1");
  assert.notEqual(themeCacheKey(1), themeCacheKey(2));
});

test("a signed-out choice does not leak into a signed-in account", () => {
  const store = fakeStorage();

  writeThemeCache("dark", null, store);

  assert.equal(readThemeCache(7, store), "system");
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

  assert.equal(readThemeCache(null, hostile), "system");
  assert.doesNotThrow(() => writeThemeCache("dark", null, hostile));
  assert.doesNotThrow(() => writeThemeCache("dark", 3, hostile));
});

test("the account theme is mirrored into a fresh cache on load", () => {
  // Correction 2: the first load on a new device has nothing cached, so
  // without this write the pre-paint script paints the default and the
  // user sees a frame of the wrong theme. This is the write the provider
  // performs when an account loads.
  const store = fakeStorage();
  const user = { id: 42, theme: "dark" };

  assert.equal(readThemeCache(user.id, store), "system"); // fresh device

  writeThemeCache(user.theme, user.id, store); // what the provider does

  assert.equal(readThemeCache(user.id, store), "dark");
  assert.equal(store.map.get("cedarlink_theme:42"), "dark");
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
  // And it must build the same namespaced key themeCacheKey() builds,
  // or a signed-in user is painted from the wrong entry.
  assert.match(html, /localStorage\.getItem\("user"\)/);
  assert.match(html, /key \+= ":" \+ id/);
});
