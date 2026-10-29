# Container advisory review

Date checked: 19 October 2026. Recommendation: keep the release gate open,
retain the tested container restrictions and use the reviewed stable distribution
updates when available. Do not mix unstable system packages into the runtime or
silently suppress advisories to obtain a green scan.

The restricted and full Debian 13 image snapshots each have 44 high OS
package/advisory matches across eight distinct CVEs. Debian's current tracker
still lists the stable trixie source-package versions as vulnerable. Several
tracker entries describe limited local attack paths or postponed updates; this
helps assess exposure but does not automatically clear the scanner gate.

| Advisory | Upstream-described trigger and current response |
|---|---|
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) | Privileged mount helper/hook behavior. The service has no mount feature. Remove setuid/setgid bits in the images, run non-root, drop capabilities and prevent privilege gains. Stable package remains flagged. |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) | A privileged operator invokes nsenter with cgroup joining. The service does not invoke this command. Do not give the container host PID/cgroup access or administrator powers. Stable package remains flagged. |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) | An authorized mount subdirectory entry follows intermediate symlinks. No service-managed mounts or user-supplied fstab are admitted. Privilege-changing helper mode bits are removed. |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) | A local attacker replaces paths involved in a privileged bind mount. Apply the same non-root/capability/no-new-privileges controls; do not mount host project trees. |
| [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) | Privileged pathname-based ACL operations follow symlinks. The service has no privileged ACL-management feature. Debian describes a new API/ABI and compatibility concerns, so an individual ad hoc library patch is not assumed safe. |
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) | The ncurses infocmp command processes crafted input. The command exists in the inspected image, but the restricted API has no execution or terminal-definition import feature. Keep this finding visible. |
| [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) | systemd-homed group-management behavior. Standard homed binary lookup/path checks in the restricted image find no homed executable. This is narrower evidence than proving every component of the source package absent. |
| [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538) | Perl Archive::Tar reads attacker-controlled sizes. The restricted API does not accept archive ingestion. Perl exists; inspected standard Archive/Tar.pm paths are absent. Retain the package finding rather than equating a few path checks with a complete dependency proof. |

The application-path statements above are a review of the restricted API, not a
claim about every legacy importer, optional provider or future agent tool. The
conclusion that these restrictions reduce exposure is an inference from the
documented triggers and tested runtime configuration, not exploit reproduction.
They do not authorize private activation or waive any CVE.

## Additional hardening implemented

All four maintained Docker definitions now remove setuid/setgid mode bits from
runtime files. Files are retained. The previous restricted image had a setuid
mount helper; new images are checked to ensure privilege-changing file modes
are absent. Application code remains owned by root; only the explicit data/log/tmp
directories are assigned to the full service account. The service therefore
cannot rewrite its installed code even if a deployment forgets a read-only mount.
Runtime qualification also uses a non-root user, read-only filesystem,
dropped capabilities and no-new-privileges. These external launch flags must also
be used in the eventual deployment; they are not all enforceable by a Dockerfile.

The application does not need these privileged helper modes. Removing them is
defense in depth, not a package-level fix. Vulnerability records and package
metadata remain present for scanning. No dpkg metadata is removed to hide matches.
No global ignore list, ignore-unfixed option, or VEX waiver is applied.

## Full image's separate Cognee finding

The full image also matches CVE-2026-58473 against `cognee==1.0.9+enhanced`.
The settings authorization/masking backport and regression evidence are described
in [F28](ADDITIONAL-FINDINGS.md). The restricted image does not include the
upstream Cognee package and has zero Python-package findings in this scan.
The full-image version match remains visible pending a reviewed release decision;
changing the package's version label is not used as remediation.

## Evidence and limits

[container-scan-summary.json](remediation-evidence/container-scan-summary.json)
records the scanned image identities, exact package matches and raw-report hashes.
Component-presence and privilege-mode checks are saved alongside the qualification
logs. Mode-only hardening does not change affected package versions; retain the
pre-hardening scan's exact image identity when comparing it with the rebuilt image.
Do not describe an unscanned rebuild as having an exact new-image vulnerability
report merely because its dependencies match an earlier snapshot.
