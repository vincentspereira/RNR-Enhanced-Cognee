# ADR-006: Encryption at Rest Using Symmetric Key Cryptography

**Status:** Accepted
**Date:** 2026-05-14
**Deciders:** Enhanced Cognee maintainers

---

## Context

Enhanced Cognee stores memory content in the shared_memory.documents table in
PostgreSQL. This content may include personally identifiable information, business
logic, API keys, or other sensitive material provided by agents. An attacker who
gains read access to the PostgreSQL host (via a misconfigured Docker network, a
stolen database dump, or host-level compromise) could read all memory content in
plain text.

Phase 10 introduced GDPR erasure support (RB-004) and audit logging. Stakeholders
reviewing the Phase 10 audit noted that content-level encryption was missing from
the compliance posture. The project must address this before any production
deployment.

The solution must:
- Encrypt content at the application layer, not rely on disk-level encryption alone
- Be simple enough to implement and operate in v1 without external infrastructure
- Not block the MCP server startup or require network calls to encrypt/decrypt
- Remain reversible so that encrypted content can be decrypted on read

---

## Decision

Use Fernet symmetric authenticated encryption from the Python cryptography library
to encrypt the content column of every memory document before it is written to
PostgreSQL. Fernet uses AES-128-CBC with PKCS7 padding and an HMAC-SHA256
authentication tag.

The encryption key is a URL-safe base64-encoded 32-byte value stored in the
environment variable ENHANCED_COGNEE_ENCRYPTION_KEY. If the variable is absent,
the server starts without encryption and logs a [WARN] at startup. This preserves
backward compatibility for development environments that do not set the variable.

Key generation at setup time:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Store the output in .env:

    ENHANCED_COGNEE_ENCRYPTION_KEY=<generated_key>

Application-layer encrypt/decrypt pattern used in the memory repository:

    from cryptography.fernet import Fernet
    import os

    _key = os.environ.get("ENHANCED_COGNEE_ENCRYPTION_KEY")
    _fernet = Fernet(_key.encode()) if _key else None

    def encrypt_content(plaintext: str) -> str:
        if _fernet is None:
            return plaintext
        return _fernet.encrypt(plaintext.encode()).decode()

    def decrypt_content(token: str) -> str:
        if _fernet is None:
            return token
        return _fernet.decrypt(token.encode()).decode()

Encrypted values are stored as standard text strings (the Fernet token is ASCII-
safe). No schema change is required for the content column type.

Key rotation is out of scope for v1. Operators who need to rotate the key must
re-encrypt all rows: decrypt with the old key, re-encrypt with the new key, update
the environment variable, and restart the server.

This decision does NOT integrate with any external key management service (AWS KMS,
HashiCorp Vault, Azure Key Vault). That integration is deferred to a future ADR.

---

## Consequences

**Positive**
- Content at rest in PostgreSQL is unreadable without the encryption key, even if
  the database host or a backup dump is compromised.
- Fernet provides authenticated encryption: a tampered ciphertext raises an
  InvalidToken exception rather than silently returning garbage.
- No external infrastructure is required; the cryptography library is a pure-Python
  wheel with no system dependencies.
- Encryption is optional at development time (key not set) and mandatory in
  production deployments (key set).

**Negative**
- Search on encrypted content requires decrypting each row before comparing.
  Full-text search indexes on the content column are no longer useful; all
  PostgreSQL-side content filtering must move to the application layer.
- Semantic search (Qdrant) is unaffected because embeddings are generated from
  plaintext before encryption and stored in Qdrant as vectors without the raw text.
- Each read or write incurs approximately 1-2 ms of additional latency per memory
  for AES-128-CBC encryption/decryption on typical developer hardware.
- Loss of ENHANCED_COGNEE_ENCRYPTION_KEY results in permanent data loss of all
  encrypted memories. Operators must back up the key independently of the database.
- Key rotation requires a manual re-encryption pass over the full documents table,
  which must be scripted carefully to avoid data loss.

---

## Alternatives Considered

**No encryption (plain text storage)**
Rejected. Any party with read access to the PostgreSQL host or a dump file can read
all memory content. Unacceptable for deployments that store personally identifiable
information or credentials.

**Asymmetric encryption (RSA or ECDSA)**
RSA encryption of arbitrary-length content requires hybrid encryption (encrypt a
random session key with RSA, then encrypt content with that key). The implementation
complexity is similar to Fernet but with higher per-operation latency due to
asymmetric key operations. Rejected because Fernet is simpler, equally secure for
this use case, and faster.

**Transparent data encryption (TDE) via PostgreSQL disk encryption or LUKS**
Disk-level encryption (e.g., LUKS on the Docker volume) protects against physical
media theft but does not protect against an attacker who has a running connection to
PostgreSQL (e.g., via an exposed port or stolen credentials). Rejected as the sole
control; it may be used in addition to application-layer encryption in hardened
deployments.

**External key management service (AWS KMS, HashiCorp Vault)**
Provides key rotation, audit logs, and access control policies. Rejected for v1 due
to operational complexity: it introduces a network dependency on startup and requires
credentials for an external service. Planned for a future ADR after v1 ships.

**Database-level column encryption (pgcrypto)**
PostgreSQL's pgcrypto extension can encrypt columns using SQL functions. Rejected
because it requires the key to be present in SQL queries, making it visible in query
logs and pg_stat_activity, which is a significant exposure.
