"""Encrypt current replacement logins for owner custody; never print plaintext.

No profile traversal, credential change, service restart, key rotation or cloud
upload. Only current authentication fields enter the encrypted payload. Existing
encryption/index/backup-signing/age private keys are excluded. Password-manager
import remains an owner action, never inferred from successful encryption.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

BASE = Path("/opt/enhanced-cognee-memory/candidates/21abf4857ca8dce8e0a3aafc725266c8d3754529")
STAGE = Path("/var/lib/enhanced-cognee-rotation/candidate-gtnhc4kc")
IDENTITY = Path("/etc/enhanced-cognee/age-recovery-identity.txt")
AGE = Path("/opt/enhanced-cognee-stores/native/usr/bin/age")
AGE_LIBRARIES = Path("/opt/enhanced-cognee-stores/native/usr/lib/x86_64-linux-gnu")
AGE_SHA256 = "529450dfeaf3055cb24d76789d0b1f5eb8cd23e03dc4add64f84776df1272b02"
SUPPORT_SHA256 = "d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef"
FIELDS = {
    "api":("ENHANCED_MEMORY_DATABASE_URL","INDEX_ARCADEDB_USER","INDEX_ARCADEDB_PASSWORD","INDEX_QDRANT_API_KEY"),
    "worker":("ENHANCED_INDEX_DATABASE_URL","INDEX_ARCADEDB_USER","INDEX_ARCADEDB_PASSWORD","INDEX_QDRANT_API_KEY","INDEX_VALKEY_URL"),
    "operator":("ENHANCED_MEMORY_DATABASE_URL","ENHANCED_JWT_SECRET"),
    "backup":("ENHANCED_MEMORY_DATABASE_URL",),
    "launch-index-authority":("INDEX_ARCADEDB_USER","INDEX_ARCADEDB_PASSWORD"),
    "launch-cache-authority":("INDEX_VALKEY_URL",),
}


def require(value,reason):
    if not value:raise ValueError(reason)


def payload(configs):
    require(configs["api"].get("ENHANCED_JWT_SECRET") == configs["operator"].get("ENHANCED_JWT_SECRET"),
            "active_signing_binding_required")
    selected = {}
    for name,fields in FIELDS.items():
        selected[name] = {}
        for field in fields:
            value = configs[name].get(field)
            require(isinstance(value,str) and 0 < len(value) <= 8192 and not any(c in value for c in "\x00\r\n"),
                    "current_authentication_fields_required")
            selected[name][field] = value
    raw = json.dumps(dict(schema=1,source_revision=BASE.name,active_authentication=selected),sort_keys=True).encode()
    require(len(raw) <= 65536,"bounded_credential_export_required")
    return raw


def protected_age():
    for path in (*reversed(AGE.parents),AGE):
        info = path.lstat()
        require(info.st_uid == 0 and not info.st_mode & 0o022 and not stat.S_ISLNK(info.st_mode),"protected_age_executable_required")
    require(stat.S_ISREG(info.st_mode) and info.st_mode & 0o111,"protected_age_executable_required")
    require(info.st_size <= 8388608 and hashlib.sha256(AGE.read_bytes()).hexdigest() == AGE_SHA256,"reviewed_age_executable_required")
    for path in (*reversed(AGE_LIBRARIES.parents),AGE_LIBRARIES):
        info = path.lstat()
        require(info.st_uid == 0 and stat.S_ISDIR(info.st_mode) and not info.st_mode & 0o022,"protected_age_libraries_required")


def age_call(arguments,raw):
    result = subprocess.run([str(AGE),*arguments],input=raw,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
        cwd="/",timeout=45,env={"PATH":"/usr/bin:/bin","LANG":"C.UTF-8","LD_LIBRARY_PATH":str(AGE_LIBRARIES)})
    require(result.returncode == 0 and 0 < len(result.stdout) <= 262144,"age_operation_failed_no_secret_output")
    return result.stdout


def encrypt_verified(raw,recipient):
    require(isinstance(recipient,str) and re.fullmatch(r"age1[023456789acdefghjklmnpqrstuvwxyz]{50,100}",recipient),
            "existing_native_age_recipient_required")
    encrypted = age_call(["--encrypt","--recipient",recipient],raw)
    require(encrypted.startswith(b"age-encryption.org/v1\n"),"native_age_ciphertext_required")
    restored = age_call(["--decrypt","--identity",str(IDENTITY)],encrypted)
    require(hmac.compare_digest(restored,raw),"credential_export_roundtrip_failed")
    return encrypted


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1,"fixed_root_operator_required")
    os.umask(0o077)
    source = Path(__file__).with_name("recover_launch_graph_operator.py").read_bytes()
    require(hashlib.sha256(source).hexdigest() == SUPPORT_SHA256,"reviewed_file_support_required")
    support = {"__name__":"verified_credential_custody_files"}
    exec(compile(source,"<verified-credential-custody-files>","exec"),support)
    read,write = (support[key] for key in ("read_file","private_write"))
    gates = [(STAGE / name / "summary.json",None) for name in (
        "postgres-operator-backup-rotation","application-signing-rotation","postgres-legacy-login-retirement","derived-legacy-login-retirement")]
    gates.append((BASE / "operator-evidence/installed-worker-projection-after-retirement/summary.json","post_retirement_qualification"))
    for path,field in gates:
        receipt = json.loads(read(path,0))
        require(receipt.get("complete") is True and (field is None or receipt.get(field) is True),"completed_rotation_retirement_and_projection_required")
    originals = {name:read(Path("/etc/enhanced-cognee") / (name+".json"),0) for name in FIELDS}
    configs = {name:json.loads(raw) for name,raw in originals.items()}
    recipient = configs["backup"].get("ENHANCED_BACKUP_RECIPIENT")
    require(configs["operator"].get("ENHANCED_BACKUP_RECIPIENT") == recipient,"existing_recipient_binding_required")
    # Validate existing identity using the same strict file protection guard;
    # its bytes never enter the export, arguments, environment or output.
    read(IDENTITY,0)
    protected_age()
    attempt = STAGE / "credential-custody-export"
    attempt.mkdir(mode=0o700)
    result = dict(complete=False,evidence=str(attempt),source_revision=BASE.name,
        credentials_changed=False,profiles_changed=False,services_restarted=False,keys_changed=False,
        plaintext_file_written=False,password_manager_custody_confirmed=False,fleet_launch_approved=False)
    write(attempt / "started.json",json.dumps(result).encode())
    try:
        raw = payload(configs)
        encrypted = encrypt_verified(raw,recipient)
        require(all(read(Path("/etc/enhanced-cognee") / (name+".json"),0) == before for name,before in originals.items()),
                "active_configuration_changed_during_export")
        destination = attempt / "current-logins.json.age"
        write(destination,encrypted)
        require(read(destination,0) == encrypted,"encrypted_export_write_not_verified")
        result.update(complete=True,encrypted_export=str(destination),encrypted_export_sha256=hashlib.sha256(encrypted).hexdigest(),
            in_memory_decryption_verified=True,configuration_group_count=len(FIELDS),
            owner_password_manager_import_pending=True,all_credentials_rotated=False)
    except Exception as error:
        result["category"] = "credential_custody_export_incomplete_preserve_evidence"
        allowed = {"active_signing_binding_required","current_authentication_fields_required","bounded_credential_export_required",
            "existing_native_age_recipient_required","age_operation_failed_no_secret_output","native_age_ciphertext_required",
            "credential_export_roundtrip_failed","active_configuration_changed_during_export","encrypted_export_write_not_verified"}
        if type(error) is ValueError and str(error) in allowed:result["reason"] = str(error)
    write(attempt / "summary.json",json.dumps(result).encode())
    print(json.dumps(result))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    try:raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"credential_custody_preflight_refused_no_secret_output"}')
        raise SystemExit(1)
