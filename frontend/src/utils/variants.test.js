/**
 * Variant resolution and the vendor/customer guards.
 *
 * `node --test`, no dependency — the logic has no React or DOM in it, which
 * is why it lives in its own module. See
 * docs/decisions/0036-variant-management-and-picker.md.
 */
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  combinationTaken,
  resolveVariant,
  selectionComplete,
  selectionValueIds,
} from "./variants.js";

const OPTIONS = [
  { id: 10, values: [{ id: 100 }, { id: 101 }] }, // Colour
  { id: 20, values: [{ id: 200 }, { id: 201 }] }, // Size
];

const VARIANTS = [
  { id: 1, option_value_ids: [100, 200] }, // Red / S
  { id: 2, option_value_ids: [101, 201] }, // Blue / M
];

test("selectionValueIds sorts and drops empty picks", () => {
  assert.deepEqual(selectionValueIds({ 20: 201, 10: 100 }), [100, 201]);
  assert.deepEqual(selectionValueIds({ 10: 100, 20: null }), [100]);
  assert.deepEqual(selectionValueIds({}), []);
});

test("selectionComplete needs a pick on every axis", () => {
  assert.equal(selectionComplete(OPTIONS, { 10: 100, 20: 200 }), true);
  assert.equal(selectionComplete(OPTIONS, { 10: 100 }), false);
  assert.equal(selectionComplete([], { 10: 100 }), false);
});

test("resolveVariant matches by id set, in any order", () => {
  assert.equal(resolveVariant(VARIANTS, { 20: 200, 10: 100 }).id, 1);
  assert.equal(resolveVariant(VARIANTS, { 10: 101, 20: 201 }).id, 2);
});

test("resolveVariant returns null for a partial or unstocked combination", () => {
  assert.equal(resolveVariant(VARIANTS, { 10: 100 }), null); // partial
  assert.equal(resolveVariant(VARIANTS, { 10: 100, 20: 201 }), null); // Red / M — no variant
  assert.equal(resolveVariant(VARIANTS, {}), null);
});

test("combinationTaken flags a duplicate, ignoring the variant being edited", () => {
  assert.equal(combinationTaken(VARIANTS, [100, 200]), true);
  assert.equal(combinationTaken(VARIANTS, [200, 100]), true); // order-free
  assert.equal(combinationTaken(VARIANTS, [100, 201]), false);
  assert.equal(combinationTaken(VARIANTS, [100, 200], 1), false); // that's variant 1 itself
});
