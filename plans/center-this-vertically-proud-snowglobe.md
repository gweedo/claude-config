# Plan: Write Tests for `src/lib/auth.ts`

## Context

`src/lib/auth.ts` is the JWT-based auth module. It has no tests today. The four exported functions interact with `next/headers`, `next/server` (NextRequest), and `jose` — none of which have been mocked in this codebase before. This plan establishes the mocking pattern and achieves full coverage of the module.

---

## New File

**`src/lib/__tests__/auth.test.ts`**

---

## Mocking Strategy

Three modules need to be stubbed at the top of the test file:

| Module | Why | How |
|---|---|---|
| `server-only` | Throws at import time outside a server context | `vi.mock('server-only', () => ({}))` |
| `next/headers` | `cookies()` reads the request context | `vi.mock('next/headers', ...)` returning a fake cookie store |
| `jose` | Crypto primitives — deterministic behaviour needed | `vi.mock('jose', ...)` with a chainable `SignJWT` stub and a controllable `jwtVerify` stub |

The fake cookie store exposes `get`, `set`, and `delete` as `vi.fn()` so each test can inspect or configure them via `mockReturnValue` / `mockResolvedValue`.

`NextRequest` can be instantiated directly (`new NextRequest('http://localhost', { headers })`) — no mock needed.

---

## Test Cases

### `createSession(userId, email)`
1. Calls `SignJWT` with correct payload (`userId`, `email`, `expiresAt`)
2. Sets the `auth-token` cookie with `httpOnly: true`, `sameSite: "lax"`, `path: "/"`
3. Sets `secure: false` when `NODE_ENV !== "production"`

### `getSession()`
4. Returns `null` when the cookie is absent
5. Returns the `SessionPayload` object when the token is valid
6. Returns `null` when `jwtVerify` throws (invalid / expired token)

### `deleteSession()`
7. Calls `cookieStore.delete("auth-token")`

### `verifySession(request: NextRequest)`
8. Returns `null` when the request has no `auth-token` cookie
9. Returns the `SessionPayload` when the token is valid
10. Returns `null` when `jwtVerify` throws

---

## Critical Files

- **Modify**: none — new file only
- **New file**: `src/lib/__tests__/auth.test.ts`
- **Read for reference** (existing test style): `src/lib/__tests__/file-system.test.ts`, `src/lib/contexts/__tests__/chat-context.test.tsx`
- **Subject under test**: `src/lib/auth.ts`
- **Vitest config**: `vitest.config.mts` (jsdom environment, tsconfigPaths)

---

## Verification

```bash
npx vitest run src/lib/__tests__/auth.test.ts
```

All 10 tests should pass with no TypeScript errors.
