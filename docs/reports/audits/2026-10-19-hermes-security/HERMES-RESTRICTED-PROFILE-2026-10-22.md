# Restricted Hermes profile - operator checkpoint

Date: 22 October 2026. This records owner-run Ubuntu-Hermes results, not direct
host observation by the Ubuntu-Workspace implementation session.

## Received approval and scope

The owner approved the restricted account and initial profile. After testing,
the objective remains the main Hermes assistant, all 40-plus bots and all other
Hermes profiles using the same protected Cognee backend, with individual scoped
identities and reviewed sharing. See the live-profile account and fleet runbooks.

## Operator results received

- Preflight identified Ubuntu-Hermes and the human user vincentspereira. The
  account, matching group and /var/lib/hermes-runtime home were absent.
- The human user's Hermes launcher is /home/vincentspereira/.local/bin/hermes.
  Its source/interpreter, permissions and accessibility by the restricted user
  have not yet been qualified.
- The protected Cognee Python executable was reported present at
  /opt/enhanced-cognee-memory/runtime/bin/python. Presence is not runtime testing.
- The owner then ran the guarded account-creation step and reported
  hermes-runtime created, home /var/lib/hermes-runtime, home permissions 0700,
  sole group hermes-runtime and password login locked. No profile was configured.

## Next qualification and limitations

Inspect the actual Hermes launcher/runtime without executing user-writable code
as root or granting broad access to the administrator's home. Verify the real
restricted agent process, sudo policy, administrative sockets, service secrets
and peer credential access. Group membership and a locked password alone do not
prove operating-system isolation. Prepare only the initial fresh invented-data
profile, its scoped credential/renewal and narrow existing model settings.

Profile backup coverage, provider/model behavior, fresh-session recall, correction,
sharing and access-denial checks remain pending for this account. No actual bot
or main-profile rollout, private-data admission, runtime reinstallation, restart
or backup run is established by the received account result. Existing service
keys, profiles, bots, history and backup generations remain subject to the
preservation requirements; the paused v12 backup workflow remains separate.
