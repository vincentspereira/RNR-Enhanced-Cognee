"""Release only verified ciphertext to an owner-readable private pickup folder.

No decryption/signing-key access, credential change or vault automation. The
owner imports the age-encrypted attachment into the existing password manager.
Only the unprivileged owner child creates files under /tmp; root never follows
an owner-controlled destination. Originals and every pickup copy are retained.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys
import tempfile
import uuid

STAGE = Path("/var/lib/enhanced-cognee-rotation/candidate-gtnhc4kc/credential-custody-export")
SOURCE = STAGE / "current-logins.json.age"
EXPECTED_SHA256 = "6951fd09ed6edcce2a3fc53f1d8f90861e8776c4a3663397091ff3e7327d4322"
SHARED_SHA256 = "d7a83e8a12f7841fc8af0f94421072784c047fee53cf07a76409e9baf141adef"
OWNER = "vincentspereira"


def require(value,reason):
    if not value:raise ValueError(reason)


def owner_copy(raw):
    account = pwd.getpwnam(OWNER)
    fields = dict(line.split(":",1) for line in Path("/proc/self/status").read_text().splitlines())
    require(os.geteuid() == account.pw_uid and account.pw_uid != 0 and account.pw_dir == "/home/"+OWNER
        and not os.getgroups() and fields["NoNewPrivs"].strip() == "1"
        and all(fields[k].strip() == "0000000000000000" for k in ("CapEff","CapAmb")),"restricted_owner_required")
    require(0 < len(raw) <= 262144 and raw.startswith(b"age-encryption.org/v1\n")
        and hashlib.sha256(raw).hexdigest() == EXPECTED_SHA256,"verified_ciphertext_required")
    os.umask(0o077)
    directory = Path(tempfile.mkdtemp(prefix="ec-owner-custody-",dir="/tmp"))
    descriptor = os.open(directory,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = os.open("current-logins.json.age",os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,0o600,dir_fd=descriptor)
        with os.fdopen(fd,"wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        fd = os.open("current-logins.json.age",os.O_RDONLY | os.O_NOFOLLOW,dir_fd=descriptor)
        with os.fdopen(fd,"rb") as stream:
            info = os.fstat(stream.fileno())
            require(info.st_uid == account.pw_uid and stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and stat.S_IMODE(info.st_mode) == 0o600 and stream.read(262145) == raw,"owner_copy_not_verified")
        os.fsync(descriptor)
    finally:os.close(descriptor)
    return dict(complete=True,owner_file=str(directory / "current-logins.json.age"),encrypted_export_sha256=EXPECTED_SHA256,
        byte_count=len(raw),plaintext_file_written=False)


def validate_receipt(value,size):
    require(isinstance(value,dict) and set(value) == {"complete","owner_file","encrypted_export_sha256","byte_count","plaintext_file_written"}
        and value["complete"] is True and value["plaintext_file_written"] is False
        and value["encrypted_export_sha256"] == EXPECTED_SHA256 and type(value["byte_count"]) is int
        and value["byte_count"] == size and isinstance(value["owner_file"],str)
        and re.fullmatch(r"/tmp/ec-owner-custody-[A-Za-z0-9_-]{6,64}/current-logins\.json\.age",value["owner_file"]),"fixed_owner_copy_receipt_required")
    return value


def main():
    require(os.geteuid() == 0 and len(sys.argv) == 1,"fixed_root_operator_required")
    os.umask(0o077)
    raw = Path(__file__).with_name("recover_launch_graph_operator.py").read_bytes()
    require(hashlib.sha256(raw).hexdigest() == SHARED_SHA256,"reviewed_support_required")
    shared = {"__name__":"verified_ciphertext_release_files"}
    exec(compile(raw,"<verified-ciphertext-release-files>","exec"),shared)
    read,write = shared["read_file"],shared["private_write"]
    prior = json.loads(read(STAGE / "summary.json",0))
    require(prior.get("complete") is True and prior.get("in_memory_decryption_verified") is True
        and prior.get("encrypted_export_sha256") == EXPECTED_SHA256,"completed_export_required")
    ciphertext = read(SOURCE,0)
    require(ciphertext.startswith(b"age-encryption.org/v1\n") and hashlib.sha256(ciphertext).hexdigest() == EXPECTED_SHA256,"verified_ciphertext_required")
    account = pwd.getpwnam(OWNER)
    source = Path(__file__).read_bytes()
    require(len(source) <= 65536,"bounded_owner_source_required")
    code = ("import json,sys\nn={'__name__':'verified_owner_ciphertext_pickup'}\nexec(compile("+repr(source)+",'<verified-owner-ciphertext-pickup>','exec'),n)\n"
        "try:\n print(json.dumps(n['owner_copy'](sys.stdin.buffer.read(262145))))\n"
        "except Exception:\n print('{\"complete\":false}');sys.exit(1)\n")
    process = subprocess.run(["/usr/bin/setpriv","--no-new-privs","--","/usr/bin/python3","-I","-B","-c",code],input=ciphertext,
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=15,cwd="/",user=account.pw_uid,group=account.pw_gid,extra_groups=(),
        env={"PATH":"/usr/bin:/bin","HOME":account.pw_dir,"LANG":"C.UTF-8","PYTHONDONTWRITEBYTECODE":"1"})
    require(process.returncode == 0 and 0 < len(process.stdout) <= 4096,"owner_copy_failed_no_secret_output")
    receipt = validate_receipt(json.loads(process.stdout),len(ciphertext))
    # Each replacement pickup gets a separate receipt; retain all earlier proof.
    receipt_path = STAGE / ('owner-copy-' + uuid.uuid4().hex + '.summary.json')
    result = dict(receipt,source_export_preserved=True,password_manager_custody_confirmed=False,
        credentials_changed=False,keys_read=False,keys_changed=False,profiles_changed=False,services_changed=False,
        vault_changed=False,fleet_launch_approved=False,evidence=str(receipt_path))
    write(receipt_path,json.dumps(result).encode())
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    try:raise SystemExit(main())
    except Exception:
        print('{"complete":false,"category":"encrypted_owner_copy_refused_no_secret_output"}')
        raise SystemExit(1)
