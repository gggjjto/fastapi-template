import assert from "node:assert/strict";
import test from "node:test";

import { cookieOptions, isSameOrigin } from "./request-security.ts";

test("auth cookies are unavailable to browser JavaScript", () => {
  assert.equal(cookieOptions.httpOnly, true);
  assert.equal(cookieOptions.sameSite, "lax");
  assert.equal(cookieOptions.path, "/api");
});

test("same-origin mutations are accepted", () => {
  assert.equal(
    isSameOrigin("http://localhost:3001/api/auth/logout", "http://localhost:3001"),
    true,
  );
});

test("cross-origin and origin-less mutations are rejected", () => {
  for (const origin of ["https://attacker.example", null]) {
    assert.equal(isSameOrigin("http://localhost:3001/api/auth/logout", origin), false);
  }
});
