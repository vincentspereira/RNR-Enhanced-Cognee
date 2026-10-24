#!/usr/bin/env bash
# Public pinned bundle only. No checkout module executes as root.
# Usage: bash run_hermes_launch_native.sh CHECKOUT FULL_PUBLISHED_REVISION [qualify|inspect|resume-answer|inspect-attempt] [EXPLICIT_TEST_ID]
set -euo pipefail
test "${WSL_DISTRO_NAME:-}" = Ubuntu-Hermes
test "$(id -un)" = vincentspereira
cognee_checkout=${1:?Supply the existing Hermes source checkout}
cognee_revision=${2:?Supply the full published source revision}
cognee_mode=${3:-qualify}
cognee_resume_id=${4:-}
[[ "$cognee_mode" = qualify || "$cognee_mode" = inspect || "$cognee_mode" = resume-answer || "$cognee_mode" = inspect-attempt ]]
if [[ "$cognee_mode" = resume-answer || "$cognee_mode" = inspect-attempt ]]; then
  [[ "$cognee_resume_id" =~ ^[0-9a-f]{24}$ ]]
else
  test -z "$cognee_resume_id"
fi
[[ "$cognee_revision" =~ ^[0-9a-f]{40}$ ]]
git -C "$cognee_checkout" cat-file -e "$cognee_revision^{commit}"
sudo -v
git -C "$cognee_checkout" archive "$cognee_revision" -- \
  'integrations/hermes/deployment/provision_pilot_access.py' \
  'integrations/hermes/deployment/install_pilot_provider.py' \
  'integrations/hermes/deployment/check_pilot_codex.py' \
  'integrations/hermes/deployment/qualify_launch_candidate.py' \
  'integrations/hermes/enhanced_cognee/__init__.py' \
  'integrations/hermes/enhanced_cognee/client.py' \
  'integrations/hermes/enhanced_cognee/plugin.yaml' |
  /usr/bin/sudo -n /usr/bin/env WSL_DISTRO_NAME=Ubuntu-Hermes /usr/bin/python3 -I -B -c 'import hashlib,io,json,sys,tarfile
expected = {'"'"'integrations/hermes/deployment/provision_pilot_access.py'"'"': '"'"'f2bf3ec50bfd8414011aa322e027f7c266a7102d558c0b7d0518549e8a8b2cc6'"'"', '"'"'integrations/hermes/deployment/install_pilot_provider.py'"'"': '"'"'410cfc4145848f5bf868c0ff1f8e7a0245057c0b53f662b8cb45a41f5d450368'"'"', '"'"'integrations/hermes/deployment/check_pilot_codex.py'"'"': '"'"'8aad07b7a40770eb89d687bc2b7c9c004f88b1b79b94304e179058e568b38695'"'"', '"'"'integrations/hermes/deployment/qualify_launch_candidate.py'"'"': '"'"'913bd50a69963ccc74656cce037c9b4fc0b066a7a8fe8ac6be46e29773d4caeb'"'"', '"'"'integrations/hermes/enhanced_cognee/__init__.py'"'"': '"'"'fcc7be3d7659671f14006f685c8e5419554075a1e35ca4dde687d7ae46400061'"'"', '"'"'integrations/hermes/enhanced_cognee/client.py'"'"': '"'"'8c57f6db374fdc3ca2db4b40c9a1b3858cd92546827043e328ce74045012af64'"'"', '"'"'integrations/hermes/enhanced_cognee/plugin.yaml'"'"': '"'"'c23230082be650ae142c4e3d8e30350ea5f3d18af5b879996328caf59d4dca48'"'"'}
try:
 raw=sys.stdin.buffer.read(1048577)
 if len(raw)>1048576: raise ValueError()
 sources={}
 with tarfile.open(fileobj=io.BytesIO(raw),mode="r:") as archive:
  for member in archive:
   if member.isdir(): continue
   if not member.isfile() or member.name not in expected or member.name in sources or not 0<member.size<=131072: raise ValueError()
   value=archive.extractfile(member).read(131073)
   if len(value)!=member.size or hashlib.sha256(value).hexdigest()!=expected[member.name]: raise ValueError()
   sources[member.name]=value
 if set(sources)!=set(expected): raise ValueError()
except Exception:
 print(json.dumps({"complete":False,"failure_stage":"public_bundle_verification"}));sys.exit(1)
namespace={"__name__":"reviewed_launch_operator"}
exec(compile(sources["integrations/hermes/deployment/qualify_launch_candidate.py"],"<reviewed-launch-operator>","exec"),namespace)
try:
 namespace["main"](sources, sys.argv[1], (sys.argv[2] or None) if len(sys.argv)==3 else None)
except Exception:
 print(json.dumps({"complete":False,**namespace["PROGRESS"],"category":"qualification_incomplete_preserve_evidence_no_automatic_retry","fleet_launch_approved":False}));sys.exit(1)
' "$cognee_mode" "$cognee_resume_id"
