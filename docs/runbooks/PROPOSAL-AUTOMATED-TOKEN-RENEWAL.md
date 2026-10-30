# Proposal: automated 30-day fleet token renewal (option 1)

Owner decision recorded 30 October 2026: keep 30-day rotation and automate
renewal. This proposal implements it and needs explicit owner approval
before installation, because it introduces an unattended root-side job
(the reviewed design until now says "no unattended issuer").

## What is proposed

One root-owned systemd timer+service pair, `ec-hermes-memory-token-renew`:

- Fires weekly (Monday 04:00) and at boot with a delay.
- Runs a hash-pinned root-owned helper (a thin loop over the reviewed
  provisioner) that renews ONLY tokens inside their final 7 days:
  default profile plus every role listed in fleet-token-receipts.json.
- Each renewal: fresh 30-day issuer-signed token, denial checks, API
  scope verification, atomic .env publication chowned to the gateway
  identity, backup retained, receipts file updated (gateway-readable).
- Never: prints token values, changes TTL/policy, enables fleet admission,
  touches profiles not in the receipts file, or runs on any host but
  Ubuntu-Hermes (hostname-pinned, like the provisioner).
- Logs a one-line sanitized summary per run to the journal; a failure
  leaves prior tokens in place (they simply keep their old expiry) and is
  visible via systemctl status.

## Why this shape

- Fail-safe: a broken timer degrades to the manual command, never to
  locked-out bots (tokens live until their printed expiry).
- Bounded: 7-day window means each token is renewed exactly once per cycle;
  a missed week still leaves 20+ days of margin.
- Auditable: same receipts file the owner can read; journal evidence per
  run; the helper is pinned by hash and refuses any modification.

## Timeline requiring attention before this is installed

- default token expires 2026-11-06 (roles: 2026-11-29). If approval lands
  after Nov 1, renew default manually first with the existing command.

## Owner approval requested

Approve installing the timer+helper (one sudo command), or decline and stay
on the manual monthly command.
