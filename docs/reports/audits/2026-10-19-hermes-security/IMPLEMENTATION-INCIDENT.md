# Implementation preservation incident

Date: 19 October 2026, Europe/London.

During the first upstream settings test import, Cognee's pre-existing logging
setup used the normal user log directory and ran its automatic retention hook.
The tool output recorded deletion of:

`/home/vincentspereira/.cognee/logs/2026-07-13_02-44-01.log`

The deletion message was observed at 22:36:13 local time. This was not an
authorized cleanup. The agent should have disabled file logging before importing
that package. The recorded impact is one observed older log deletion; its content
has not been recovered. No copy was found in the specific audit/temporary backup
locations checked. This does not establish that no separate owner backup exists.
No speculative disk-recovery or host changes were attempted.

Correction: the import-time cleanup no longer deletes files. Qualification
processes, container defaults and CI now disable file logging and dotenv loading.
Explicit dotenv use cannot override pre-existing environment settings. A fixture
with twelve existing logs and a nominal retention count of two confirms that all
twelve remain intact. Source originals were archived before changing the logger.

The incident was disclosed to Vincent during implementation. It does not justify
claiming that every pre-existing file was preserved without exception.
