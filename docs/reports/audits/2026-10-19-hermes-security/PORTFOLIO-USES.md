# Uses for Enhanced Cognee across the portfolio

Date: 19 October 2026

These are proposed integrations, not claims that the projects already use this
memory service or have passed production/release gates. Their safe adoption
depends on the security and correctness repairs in the accompanying audit.

## Recommended first use

Start with engineering decisions and approved RNR-Brain project notes. These
have a clear retrieval need and can be piloted with text already intended for
project collaboration. Keep each project's private facts separate; share only
an explicitly curated reference collection.

The useful role is a searchable knowledge and evidence layer. Each project's
existing database, files, and approved records remain authoritative for their
own operational state. Recalling a claim does not authorize an action.

## Candidate uses

| Priority | Project/system | Useful memory | Example question | Boundary |
|---|---|---|---|---|
| First | RNR-Brain / portfolio coordination | Approved product decisions, source links, dependencies, reasons for choices | Why did we choose this architecture, and what must be completed before the next phase? | Preserve dated sources, conflicting claims, and owner approval status |
| First | Development assistants and MAS SDLC agents | Resolved bugs, architecture decisions, interface contracts, tested migration notes | Have we solved this failure before, and which code revision proves it? | Reference source commit/test evidence; no automatic merge or production changes |
| Early | RNR-Spatial-Engine | Asset/model capability notes, provenance, workflow recipes, license-review references, dated test findings | Which approved workflow can produce this output, and what evidence is missing? | Existing manifests/evidence remain authoritative; recalled readiness is never permission |
| Early | RNR-Marketing-and-SEO-System | Audience research, approved messaging, campaign hypotheses, measured experiment history | What did the previous campaign test, and which findings were actually observed? | No automatic posting, spend, account activation, or mixing simulated with observed results |
| Early | RNR-File-Converter | Conversion recipes, known format limitations, error resolutions, documentation search | Which settings solved this layout issue on a similar document? | Keep conversion local; do not retain customer documents by default; pricing/config remain authoritative elsewhere |
| Early | Faith Channel | Sources, editorial decisions, content continuity, rights/consent references | Which approved source supports this script, and has this theme already been used? | Keep private family media out; distinguish research/modelled results from channel analytics |
| Later | RNR-Polyglot-Productivity-Suite / notebook-style research | Terminology, user-approved writing preferences, topic/source relationships | Which terminology and source passages should remain consistent across these documents? | User/project separation and document authority; do not reproduce restricted source corpora blindly |
| Later | Odoo/accounting/taxation workflows | Approved procedure notes, document references, explanations of reconciliations | What evidence supported this reconciliation and who reviewed it? | Ledger and source records remain authoritative; no filing, payment, or compliance decision from memory alone |
| Later | ATS and financial-analysis research | Experiment metadata, candidate rationale, rejected hypotheses, validation evidence | Was this candidate rejected, under which test, and was its dataset held out? | Research/paper scope; no broker credentials, order authority, or inference that past evidence guarantees performance |
| Separate review | RNR-Family-Gateway | Opt-in household guides, support notes, approved FAQs | Where is the approved troubleshooting guide for this device? | Do not centralize live location, child/family communications, or encryption keys in a broad agent store |
| Separate review | Legal/social-work or sensitive personal-finance systems | Permission-controlled source indexes and approved case/procedure notes | Which current source and reviewed note support this answer? | Separate deployments/keys if appropriate; tightly controlled access, retention, and expert verification |

## Four reusable integration patterns

1. **Project librarian:** index selected documentation with source paths and commit
   hashes. Start with read-only recall and explicit owner-approved updates.
2. **Decision memory:** store a decision, alternatives, rationale, supporting
   evidence, owner, date, and revisit condition. Preserve later corrections.
3. **Incident memory:** store a sanitized symptom, cause, fix, affected versions,
   and passing evidence. Use it to suggest investigations, not run them blindly.
4. **Research graph:** connect claims, entities, sources, and experiments. Return
   traceable references and show uncertainty when sources disagree.

Chat assistants can use a qualified MCP interface; applications can call a
qualified REST API through backend code. Existing SDKs need contract repairs
before being treated as interchangeable. Browser/mobile applications should
never receive the service's operator key or database credentials.

## Data organization

```text
Enhanced memory platform
  Private project stores
    Brain
    Spatial
    Marketing
    File Converter support knowledge
    Faith editorial knowledge
    Other approved projects
  Explicitly shared reference material
    Reusable engineering procedures
    Approved public research and license references
  Separate sensitive deployments where required
    Family, client casework, or regulated records
```

Names and categories are configuration, not hardcoded enums. A project label
does not replace an access-control policy. Source facts should retain their
original authority; a memory should say that a dated report asserted something,
not silently convert that assertion into present-day verified truth.

## Pilot and success criteria

Choose one engineering project and 20-30 non-sensitive decision/incident notes.
Create questions before indexing, including paraphrases, two-source questions,
corrections, and deliberate no-answer questions. Compare ordinary text retrieval
with the proposed semantic/graph path.

Measure correct source retrieval, unsupported answers, cross-project leakage,
correction behavior, latency, processing calls, and local resource use. Set the
adoption threshold with Vincent after seeing the baseline. Do not invent a
percentage improvement from the architecture or existing load-test claims.

Only expand when the new memory actually helps answer useful questions and its
permissions, recovery, and maintenance costs are understood. General search,
transactional state, raw file storage, and every conversation do not all need
to become a knowledge graph.

## Portfolio-source basis

This audit inspected the current README introductions for RNR-Brain,
RNR-Spatial-Engine, RNR-File-Converter, RNR-Family-Gateway,
RNR-Multi-Agent-AI-System, and RNR-Social-Media-Faith-Channel. Other named systems
are proposals based on the supplied project catalog and prior portfolio context;
their present implementation was not audited here. None of these project-use
examples is a new readiness or commercial qualification claim.
