# SDK Publishing Guide

How to publish the three new client SDKs (Node / Go / Rust) to their respective public registries. The Python SDK is already on PyPI as `enhanced-cognee-client`.

All three registries are **free** for public packages.

## TL;DR -- one-time setup

1. Create accounts (~5 min total):
   - npm: https://www.npmjs.com/signup
   - crates.io: https://crates.io/ (sign in with GitHub)
   - pkg.go.dev needs no account
2. Generate tokens:
   - npm: Account -> Access Tokens -> Generate New Token (type: "Automation")
   - crates.io: Account Settings -> API Tokens -> New Token
3. Add to repo secrets:
   ```bash
   gh secret set NPM_TOKEN              # paste npm automation token
   gh secret set CARGO_REGISTRY_TOKEN   # paste crates.io API token
   ```
4. Push a tag to trigger the publish workflow:
   ```bash
   git tag clients-node-v1.0.0 && git push origin clients-node-v1.0.0
   git tag clients-rust-v1.0.0 && git push origin clients-rust-v1.0.0
   git tag clients-go-v1.0.0   && git push origin clients-go-v1.0.0
   ```

The `.github/workflows/publish-clients.yml` workflow handles the rest.

---

## Per-registry details

### npm (Node SDK)

**Registry:** https://www.npmjs.com/
**Package name:** `@enhanced-cognee/client`
**Cost:** free for unlimited public packages; paid plans only for private orgs.

#### Account + token

1. Sign up at https://www.npmjs.com/signup. Use a memorable username; you can't change it later.
2. Verify email.
3. Decide on scope ownership:
   - **Personal scope** (`@<your-username>/client`): default, no extra setup.
   - **Org scope** (`@enhanced-cognee/client`, our case): create the org at https://www.npmjs.com/org/create. Free tier supports unlimited public packages per org.
4. Enable 2FA (Account Settings -> Profile -> Two-Factor Authentication). Required for "Automation" tokens which we use.
5. Generate a token: Account -> Access Tokens -> Generate New Token -> "Automation" type. Scope it to publish only on `@enhanced-cognee/client`.
6. Copy the token and add to GitHub repo secrets:
   ```bash
   gh secret set NPM_TOKEN
   # Paste the token when prompted
   ```

#### Manual dry-run (optional, before first real publish)

```bash
cd clients/node
npm install
npm run build
npm pack --dry-run
```

This produces a tarball preview without uploading anything. Inspect to confirm the files included are correct.

#### Tagged release

```bash
# Bump version in clients/node/package.json first (e.g. 1.0.0 -> 1.0.1)
# Then:
git add clients/node/package.json
git commit -m "chore(clients/node): bump to 1.0.1"
git push
git tag clients-node-v1.0.1
git push origin clients-node-v1.0.1
```

The `publish-node` job in the workflow will:
1. `npm ci` to install deps
2. `npm run build` to produce `dist/`
3. `npm test` to run the test suite
4. `npm publish --provenance --access public`

`--provenance` adds a verifiable build attestation linking the package to this GitHub Actions run -- shows up as a green "Provenance" badge on npmjs.com.

### crates.io (Rust SDK)

**Registry:** https://crates.io/
**Crate name:** `enhanced-cognee-client`
**Cost:** free for unlimited public crates.

#### Account + token

1. Sign in at https://crates.io/ using GitHub OAuth. No password.
2. Verify your email under Account Settings -> Email.
3. Generate a token: Account Settings -> API Tokens -> New Token. Give it a descriptive name like "GitHub Actions publish". You can scope it to `publish-update` on a specific crate, but for the first publish (when the crate doesn't exist yet) the token needs `publish-new`.
4. Copy the token (shown only once) and add to GitHub repo secrets:
   ```bash
   gh secret set CARGO_REGISTRY_TOKEN
   ```

#### Manual dry-run (optional)

```bash
cd clients/rust
cargo test --no-fail-fast
cargo publish --dry-run
```

#### Tagged release

```bash
# Bump version in clients/rust/Cargo.toml first
git add clients/rust/Cargo.toml clients/rust/Cargo.lock
git commit -m "chore(clients/rust): bump to 1.0.1"
git push
git tag clients-rust-v1.0.1
git push origin clients-rust-v1.0.1
```

The `publish-rust` job will:
1. Install Rust toolchain
2. `cargo test --no-fail-fast`
3. `cargo publish --token "$CARGO_REGISTRY_TOKEN"`

Once published, the crate auto-appears at https://crates.io/crates/enhanced-cognee-client and docs.rs auto-builds documentation within ~5 minutes.

### pkg.go.dev (Go SDK)

**Registry:** none -- pkg.go.dev is a documentation site, not a package registry.
**Module path:** `github.com/vincentspereira/RNR-Enhanced-Cognee/clients/go`
**Cost:** free, no account, no token.

#### How Go module publishing actually works

Go modules use **Git tags as the publication mechanism.** When someone runs `go get github.com/.../clients/go@v1.0.1`, the Go toolchain queries `proxy.golang.org`, which queries GitHub for the matching tag, and downloads the source tree at that commit. pkg.go.dev (the docs site) auto-indexes within ~30 minutes of the first `go get` for a new tag.

There's no upload step. There's no API token. There's no account.

#### Caveats

1. **Tag format must be exact:** `clients-go-vMAJOR.MINOR.PATCH`. The workflow uses this prefix to separate Go SDK tags from the other SDK tags in the same monorepo.

   **But:** Go's `go get` expects the tag to literally be `vMAJOR.MINOR.PATCH` (no prefix). For a monorepo subfolder, the Go convention is `<subdir>/<vTag>`, e.g. `clients/go/v1.0.1`. We use the `clients-go-v` prefix in CI for consistency with the other SDKs, but actual Go consumers MUST use the `clients/go/v1.0.1` tag.

   So push BOTH:
   ```bash
   git tag clients-go-v1.0.1       # for CI workflow trigger
   git tag clients/go/v1.0.1       # for Go consumers (go get ...@v1.0.1)
   git push origin clients-go-v1.0.1 clients/go/v1.0.1
   ```

2. **Verify after pushing:**
   ```bash
   go list -m github.com/vincentspereira/RNR-Enhanced-Cognee/clients/go@v1.0.1
   ```

   If proxy.golang.org hasn't indexed yet (~30 min), this returns an error; retry later.

3. **pkg.go.dev URL** appears at:
   ```
   https://pkg.go.dev/github.com/vincentspereira/RNR-Enhanced-Cognee/clients/go
   ```

   Triggered on the first `go get` from any user; you can warm it by running `go list -m ...@latest` from any machine.

#### Tagged release

```bash
# Bump module version reference in clients/go/README if any
# Then:
git tag clients/go/v1.0.1            # canonical Go tag
git tag clients-go-v1.0.1            # CI trigger tag
git push origin clients/go/v1.0.1 clients-go-v1.0.1
```

The `publish-go-noop` job runs `go test ./...` to confirm the tag is healthy, then prints a notice explaining that proxy.golang.org handles the actual publication.

---

## Version bumping policy

Use [semver](https://semver.org/):

- `v1.0.x` -- bug fixes; backwards-compatible
- `v1.x.0` -- new features; backwards-compatible
- `vx.0.0` -- breaking changes; bump every consumer

The four SDKs (Python, Node, Go, Rust) should track the same major version when they expose the same API surface. Python is currently at `1.0.0`; the three new SDKs should start at `1.0.0` to match.

Bump all four together when the underlying MCP HTTP contract changes.

---

## Dry-running the workflow without publishing

```bash
gh workflow run publish-clients.yml \
  -f client=node \
  -f dry_run=true
```

This runs the full test + build + pack steps but skips the `npm publish` / `cargo publish` step. Useful for confirming the workflow works before you have the registry token wired up.

---

## Rotation

If a token leaks:

1. Revoke it immediately:
   - npm: Account -> Access Tokens -> Revoke
   - crates.io: Account Settings -> API Tokens -> Revoke
2. Generate a new one.
3. Update the GitHub secret:
   ```bash
   gh secret set NPM_TOKEN              # paste new token
   gh secret set CARGO_REGISTRY_TOKEN   # paste new token
   ```

The old token stops working immediately on revoke; the new secret takes effect on the next workflow run.

## See also

- [`docs/SECRETS_MANAGEMENT.md`](SECRETS_MANAGEMENT.md) -- broader secrets handling story
- [`clients/python/README.md`](../clients/python/README.md) -- existing Python SDK already on PyPI
- [`.github/workflows/publish-clients.yml`](../.github/workflows/publish-clients.yml) -- the workflow itself
