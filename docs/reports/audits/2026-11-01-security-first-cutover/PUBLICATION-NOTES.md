# Publication notes

The reviewed payload was committed on the separate task branch as
b0598c1ae94283b56fcfcc31b5838709c85a8664. It contains the exact reviewed helper
and owner commands, canonical component tests, and selected sanitised reports,
receipts and sealed archives. This note and final staging receipts are a small
metadata follow-up; they do not modify the accepted helper or owner commands.

Initial staging stopped because the repository's generic log exclusion ignores
*.log. The partially staged index was read back, then only the explicit selected
synthetic/sanitised test logs were added. No global ignore rule was disabled,
no blind recursive force-add was used, and no synthetic sandbox, symlink or FIFO
was promoted. The original publication inventory and subsequent stage readback
preserve the exact selected path/hash set.

Source, canonical tests and maintained owner documents passed the scoped Git
whitespace check (exit 0). Full evidence whitespace checking exited 2 for retained
raw failed-test output at these relative paths:

- implementation/01-red.log
- repair-round1/original-current-source/junit.xml
- repair-round1/original-current-source/process.log
- repair-round1/red-regressions/junit.xml
- repair-round1/red-regressions/process.log
- repair-round1/reviewer-obsolete-fixture/junit.xml
- repair-round1/reviewer-obsolete-fixture/process.log

Trailing spaces inside their captured pytest tracebacks were not rewritten to
make a cosmetic check pass. This exception does not cover executable source or
ordinary authored documentation. parent/publication-full-whitespace.log preserves
the complete original checker output, not a claim that the full tree was clean.

Local retained sandboxes and some run-output metadata remain outside publication;
they were not deleted or interpreted as live deployment. Full hosted CI was not
verified. Protected helper installation, actual owner-root plan, exact-digest
bundle preparation and any later API installation/restart remain owner gates.
