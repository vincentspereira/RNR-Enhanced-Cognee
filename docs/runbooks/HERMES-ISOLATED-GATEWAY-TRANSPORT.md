# Isolated gateway transport - local kernel identity qualification

Daily candidate backup installation passed for all 41 candidates. Main provider,
scope/index/OS checks and all 40 named credential/reload/recovery passes are
retained. This step implements and tests a necessary transport boundary for a
future shared frontend and separately owned bot runtimes. It does not implement
the complete native dispatcher or approve production admission.

Run one finite command in the owner's Ubuntu-Hermes terminal:

```bash
sudo /opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529/runtime/bin/python -I /home/vincentspereira/agent-workspace/enhanced-cognee-deployment-20261020/launch-worktree-20261024/integrations/hermes/deployment/launch_control.py qualify-isolated-transport
```

The operator reads protected completed backup evidence and requires the exact
same disabled profile identities as its 41-member backup registry. Two existing
restricted named identities are temporarily used for invented transport roles.
They are not admitted as production frontends. No account is created, profile
tree read, token issued, key read, agent turn run, external connection made,
gateway/adapter started or installed unit changed.

Each case passes a root-created anonymous Unix stream descriptor to two
separately owned processes. Kernel listener credentials remain those of the
descriptor creator, while per-message credentials identify the actual sender.
The channel checks both explicitly, including every header/body read. This
distinction is documented by [Linux unix(7)](https://man7.org/linux/man-pages/man7/unix.7.html).
The production listener must enable SO_PASSCRED before any client data arrives;
the qualifier does so before descriptor handoff. This is descriptor-handoff
testing, not proof of installed systemd socket activation.

All real/effective/saved UID/GID values must match the selected restricted
identity. Extra groups, effective/ambient/inheritable capabilities and privilege
gain are refused. The qualifier tests a valid round trip, an actual different
sender UID and a different fixed profile binding. Model/tenant/credential/UID
override fields are outside the closed wire contract. Frames/text have hard
budgets and deadlines; duplicate fields, nonfinite numbers, malformed UTF-8,
invalid text and unexpected descriptor passing are refused. Received foreign
descriptors are closed. Raw message content is never logged or made durable.

The prepared initial transport supports text request/response/cancel envelopes.
It does not yet carry media, native approval/clarification events or implement
session persistence/idempotent native dispatch. Those capabilities and the
native WhatsApp/CLI adapter integration remain explicit implementation gates.
Source tests include actual same-user Linux sockets and forged-root-credential
refusal; the protected command establishes the different-UID boundary.

Exact public source and context are frozen in
`operator-isolated-gateway-transport-v1`. Immutable case receipts and a final
summary remain under operator-evidence. Repeating a completed/failed command
returns retained evidence and never runs completed cases again. Interrupted
processes are stopped; partial effects are preserved for reconciliation.
The completed historical memory records are neither read nor edited.

Return only the final JSON summary. A transport pass reports
kernel_authenticated_transport_qualified=true while native integration,
production_dispatch_qualified, actual admission and fleet approval remain false.
