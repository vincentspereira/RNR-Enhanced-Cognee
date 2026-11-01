# Read-only Z.ai DNS comparison in Ubuntu-Hermes

Use after the restricted Coding Plan check reports category=dns_error. This
does not establish a rejected credential, quota issue or model failure. The
reported cause is a name-resolution error in the SDK exception chain, before
an SDK completion was received. Do not repeat model requests before diagnosing
resolution. Do not edit resolv.conf, WSL settings, firewall, mounts or service
identities based on this result alone.

Run the following block as the normal vincentspereira operator in Ubuntu-Hermes.
No Git fetch is needed: the diagnostic must also work when GitHub DNS fails.
It checks the same protected Python with a clean environment and
no-new-privileges under each existing account. Only stdlib code executes, under
the selected non-root identity. sudo is used only for the identity switch.
There are no model/HTTP requests, private configuration reads or file writes.
DNS lookups use the existing host resolver. Local resolver/host-file contents,
resolved addresses and raw errors are never printed. Public control and OpenAI
hostnames distinguish a possible Z.ai-specific failure from a broader resolver
failure; these lookups do not qualify either provider's authentication or model.
Each account is bounded to 20 seconds; a timeout can leave later lookups unrun.

```bash
(
  set -euo pipefail
  test "${WSL_DISTRO_NAME:-}" = "Ubuntu-Hermes"
  test "$(id -un)" = "vincentspereira"
  sudo -v
  cd /tmp

  cognee_dns_probe='
import json
import pwd
import os
import socket

account = pwd.getpwuid(os.geteuid()).pw_name
if account != os.environ["USER"] or account not in {"vincentspereira", "hermes-runtime"}:
    raise SystemExit("STOP: Unexpected diagnostic account.")
files = {}
for name in ("/etc/resolv.conf", "/etc/nsswitch.conf", "/etc/hosts"):
    try:
        with open(name, "rb"):
            files[name] = True
    except OSError:
        files[name] = False
print(json.dumps({"account": account, "system_resolver_files_readable": files}), flush=True)
for hostname in ("github.com", "api.openai.com", "chatgpt.com", "api.z.ai"):
    try:
        answers = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        result = {"resolved": bool(answers), "dns_error": None}
    except socket.gaierror as error:
        names = ("EAI_AGAIN", "EAI_NONAME", "EAI_FAIL", "EAI_SYSTEM", "EAI_FAMILY", "EAI_SERVICE", "EAI_ADDRFAMILY")
        category = next((name for name in names if getattr(socket, name, None) == error.errno), "other_dns_error")
        result = {"resolved": False, "dns_error": category}
    except Exception:
        result = {"resolved": False, "dns_error": "other_lookup_error"}
    print(json.dumps({"account": account, "hostname": hostname, **result}), flush=True)
'

  for cognee_dns_account in vincentspereira hermes-runtime; do
    if /usr/bin/timeout --kill-after=2s 20s \
      /usr/bin/sudo -n -u "$cognee_dns_account" -- \
      /usr/bin/setpriv --no-new-privs -- \
      /usr/bin/env -i USER="$cognee_dns_account" PATH=/usr/bin:/bin LANG=C.UTF-8 \
      /opt/hermes-runtime/releases/4d04303818b6-1729494fe783-tools1/venv/bin/python \
        -I -B -c "$cognee_dns_probe"; then
      :
    else
      cognee_dns_exit=$?
      printf "DNS diagnostic for %s stopped with exit %s\n" "$cognee_dns_account" "$cognee_dns_exit"
    fi
  done
)
```

Return only the public lines. An unreadable resolver file, account-specific
failure, target-specific failure, transient EAI_AGAIN or broad failure requires
different follow-up. Readability alone does not prove correct resolver content,
DNS server reachability or sufficient network access. Matching success can mean
a transient issue cleared; it does not qualify TLS, credentials or the model.
Do not substitute an IP address, disable TLS, enable proxies, change public DNS
or relax account/isolation settings without reconciling the actual evidence.

Preparation checks validate shell syntax, embedded Python syntax and fixed
public output using fixture DNS results in Workspace. These are not native
Ubuntu-Hermes resolver evidence. Actual comparison is pending the owner run.

## Owner-relayed normal-account results and OpenAI fallback

The owner relayed two Hermes reports: api.z.ai returned EAI_AGAIN under
vincentspereira; GitHub resolved in both rounds, and api.openai.com/chatgpt.com
resolved in the second. The three resolver files were readable. Neither report
executed the restricted-account probe: non-interactive sudo required operator
authentication. This is not a failed restricted DNS test. It also shows the
observed problem is not established as unique to hermes-runtime. It does not
prove a remote Z.ai outage or rule out selective/intermittent local DNS trouble.

The owner must run the block above in a normal Ubuntu-Hermes terminal and enter
their Linux password at sudo -v. Hermes should not collect that password or
receive new sudo privileges. The loop now checks control/OpenAI names first so
a slow Z.ai lookup cannot prevent their comparison. The 20-second account bound
still applies; a timeout is incomplete evidence, not failure of every hostname.

Hermes reported its existing chat used gpt-6.1-sol through openai-codex. That is
reported human-profile context, not a restricted-pilot completion. Preserve all
defaults. The pinned Hermes
[provider declaration](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/hermes_cli/providers.py)
selects codex_responses and OAuth for openai-codex, distinct from the general
API route. Its
[Codex auth resolver](https://github.com/NousResearch/hermes-agent/blob/4d04303818b61bf3aa09278af48356315515965b/hermes_cli/auth_codex.py)
uses Hermes-local auth state and can import/refresh/persist grants on ordinary
runtime paths. Do not invoke those paths merely to diagnose DNS. Do not copy,
symlink, pass through stdin, expose via environment, or share the human account's
OAuth access/refresh credentials with the restricted account. Do not change
CODEX_HOME to share authentication or substitute a pay-as-you-go API key.

Official [OpenAI authentication documentation](https://learn.chatgpt.com/docs/auth)
distinguishes subscription login from API-key billing. The
[App Server documentation](https://learn.chatgpt.com/docs/app-server) gives
gpt-6.1-sol examples while requiring account/workspace access. These do not
prove the restricted Hermes profile has an authorized connection. A protected
broker or independently signed-in restricted context would require its own
implemented/qualified path; neither is established by the relayed report.
Do not create a new login, broker or credential store during this DNS-only step.
Continue the authorized fallback review after the operator comparison, and
report an authentication boundary as such rather than claiming OpenAI failed.

## Direct operator comparison received

Both accounts resolved github.com, api.openai.com and chatgpt.com, and both
returned EAI_AGAIN for api.z.ai. All three resolver files were readable under
both identities. This supersedes the pending restricted comparison above.
It provides no reason to relax account permissions. It does not establish TLS,
OpenAI authentication/model access or the cause of the selective DNS failure.
Proceed with the authorized OpenAI fallback using independent pilot sign-in;
do not retry Z.ai or change DNS/isolation to bypass the observed failure.
