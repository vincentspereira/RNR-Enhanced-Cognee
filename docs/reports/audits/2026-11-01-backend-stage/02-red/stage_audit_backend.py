#!/usr/bin/python3
"""Fixed-target stage-only source overlay. Stdlib only; never launch application code."""
import json

COMMIT = 'c14f595ccd53f432b455b16f116765d9aa6c9a14'
# Reviewed byte bindings, not caller-supplied policy.
BINDINGS = {
    'src/ingestion.py': ('205d1c72ad937db1fa2990f3bcdba29599eceec9c17dae9e467c84b55749a821', 'b814d10674a13ac6e7ed8f1be7de5eec5ae215109dafd85bf524d6f6ba94c32b'),
    'src/llm_summarize.py': ('6a20835307a697ff401138f8fc67a6c3c8bfbb109203070da3f02812df5c78cf', 'e78c3c7fae47afe6c6228d6cab7b45387fb375f8c07ca37261a606e79a4010ae'),
    'src/llm_budget.py': (None, '81a4ddc2ef5aee073b814a428a112cabe3536f4e83cbd7a0e15c83522b8d10a7'),
    'src/memory_api.py': ('e21ba22d0bf02fee1c4ce2b1b0720dfa2fc2130118ac6e54ee0225285edd07d0', '4f125fb6d01719440a0b6c614a7767bbe386c73756b19e232e1fd481a7b64dda'),
    'src/memory_daemon.py': ('64abec3c2883b0efcf718c17e52083156b5db41f1da0bd37b7d2035960b85909', 'c0e97e285e30232467207e767a66dff2201e9041b62aeee07cada3619ee65d20'),
    'src/memory_library.py': ('7cb28171050a55d2046e7977c8ab603cc9bfbe3bc748d3efab87d263817cebcd', '9ca8bec14760ca2793b175bf69d088ed1a78eb9a5a06a94a744929ec3aa4ef2f'),
    'src/memory_queries.py': ('0d75ea1dcdc331c28bedfb4c090310035d354820a36a55960cfb7299d77be561', 'be051d645535239d57677a8a9d05bf47929d9c80f5e49d3e3884ea47e9c275a3'),
    'src/security/enterprise_auth.py': ('e9c117d5ab50bb557804ab6b3bb756ce73b918782f1a7e831b90baeabd490993', '78cf82b8d052c74438dc85b9b24393128e837dbb8bfee78eda8146dbef66ae1e'),
}


class Rejected(ValueError):
    """Fail closed, preserving any partial candidate."""


def load_manifest(data):
    return json.loads(data)
