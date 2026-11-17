# GitHub-backed replay comments

## Architecture
A separate GitHub App (NOT giscus) installed only on handizheng232-eng/Macro uses Discussions read/write + mandatory Metadata read-only, no account permissions/webhooks. No OAuth scopes are requested. Existing Discussion #1 is the sole source of comments; nothing is migrated or deleted by deployment.

Worker + one SQLite-backed Durable Object stores expiring hashed app sessions and encrypted GitHub user tokens, serializes local mutations and consumes OAuth states/exchange codes once. Browser opens OAuth popup; exact origin/source checks plus browser PKCE bind a one-time opaque exchange code. An independent server PKCE verifier protects GitHub OAuth. No third-party cookies, tokens in URL/localStorage, giscus session access, or impersonating installation-token writes. Reload requires explicit login. Session is 1 hour maximum; no refresh token persistence.

API: GET /health; POST /auth/start {challenge}; GET /auth/callback?state&code (GitHub only); POST /auth/exchange {code,verifier}; POST /auth/logout; GET /me; GET /comments?after; GET /comments/:id/replies?after; POST /comments {body,replyToId?}; PATCH /comments/:id {body,updatedAt}; DELETE /comments/:id {updatedAt}. JSON errors have error; conflicts 409; anonymous write 401; bad origin 403. Comments and replies paginate separately with totalCount/pageInfo. Mutation readback is mandatory. Delete of a parent with replies is refused (manage on GitHub), not silently cascading. updatedAt is checked before edit/delete; GitHub has no conditional mutation CAS, so external concurrent edits have a residual race and this is not a strict atomic lock across GitHub clients.

## Configuration
Non-secret Worker vars: APP_ID, CLIENT_ID, INSTALLATION_ID, WORKER_ORIGIN (exact HTTPS origin). SITE_ORIGIN is fixed https://handizheng232-eng.github.io (NO /Macro). GitHub App callback must be WORKER_ORIGIN/auth/callback; disable webhook and request user authorization with expiring user tokens. Register a separate app; install only Macro. Users without GitHub accounts register at GitHub, not on this service.
Secrets entered by user in Cloudflare dashboard, never chat: CLIENT_SECRET; APP_PRIVATE_KEY (paste downloaded PEM into the Cloudflare secret field; PKCS#1 RSA and PKCS#8 formats both supported server-side); TOKEN_KEY (base64 32 cryptographically random bytes). Do not inspect or print secret values. Rotation of TOKEN_KEY invalidates stored sessions; revoke user authorizations at GitHub if necessary.
Account ID (parent verified, non-secret): 879d8cb90a1c2b5c35fa12cb76946554. Wrangler is pinned to 4.163.0. This candidate uses SQLite Durable Objects via a Worker migration, NOT a Workers KV namespace and NOT D1. Parent should verify that its workers_scripts:write authorization supports the migration; do not expand scopes or replace storage with non-atomic KV. If D1 is mandatory, migrate the storage adapter with atomic DELETE RETURNING and write serialization tests before deploying.

GitHub App creation: homepage https://handizheng232-eng.github.io/Macro/; callback WORKER_ORIGIN/auth/callback; webhook disabled; Repository permissions Discussions read/write, Metadata read-only; all other repository/account/organization permissions No access. Make the app available for user authorization, install only Macro. Keep "Request user authorization during installation" OFF: users must enter through /auth/start to create server state/PKCE. Do not configure giscus as the new app or alter Discussion #1.

Routine deployment uses project-local `npx wrangler deploy` then `npx wrangler deployments status`. Never regenerate or inspect existing secrets. The checked-in configuration is production; do not add a development override. Normal deployment removes temporary localhost CORS access. Public Pages builds explicitly set VITE_COMMENTS_API to the exact Worker origin AND VITE_CUSTOM_COMMENTS_ENABLED=true. Defaults retain giscus. A rollback needs a separately reviewed successor publication receipt; no discussion migration is needed.

## Local commands and boundaries
Run from comments-worker: `npm ci`, `npm test`, `npm run dev` using Node 22. Public identifiers and the Worker origin are populated in wrangler.jsonc; secret values live only in Cloudflare. Health configuration presence is not provider connectivity or OAuth acceptance. Local preview cannot log in once temporary development CORS is removed.

Unit/integration provider data is explicitly fixture-only. Real anonymous reads, deployment identity and production CORS require separate checks. The user independently exercised local login and deletion before publication; this is not automated full create/edit/delete acceptance. Never alter existing user comments for QA. Unobserved operations and Safari remain unverified. No D1/KV resources are required.

Concurrency limit: the singleton DO serializes calls made through this service, but GitHub does not expose an atomic updatedAt compare-and-swap mutation; edits made directly on GitHub can race between check and update. A preflight mismatch is 409; post-write mismatch is an unconfirmed error. Do not market this as globally atomic optimistic locking. Requests with unknown write outcomes never auto-retry; users must refresh and compare before resubmitting. Parent-comment deletion with any reply is refused; an external reply arriving concurrently can cause GitHub to retain a deleted placeholder, and readback accepts only absent/deletedAt state, not a successful mutation acknowledgement.

Sessions expire after at most one hour; tokens remain encrypted, identifiers hashed. Logout deletes the application session without depending on GitHub availability, but does not revoke the user’s entire GitHub App authorization. App uninstall/user revocation is checked on authenticated requests. On Worker secret/key rotation old sessions may become unreadable; renew login. For sustained public traffic, review DO singleton throughput, abuse limits and account billing before enabling.

## Official references checked 2026-11-17
- https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app (GitHub Apps use permissions, not OAuth scopes)
- https://github.blog/changelog/2025-07-14-pkce-support-for-oauth-and-github-app-authentication/
- https://docs.github.com/en/graphql/guides/using-the-graphql-api-for-discussions
- https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app
- https://developers.cloudflare.com/workers/configuration/secrets/
- https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/
