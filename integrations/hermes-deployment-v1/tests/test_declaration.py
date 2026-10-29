"""Test dependency declaration using the genuine PM reader, without syncing PM."""
import sys
from pathlib import Path

HOST = Path('/home/vincentspereira/agent-workspace/hermes-agent')
sys.path.insert(0, str(HOST))
from pm.plugin_declarations import read_python_declaration


def test_directory_declares_all_selected_runtime_dependencies():
    candidate = Path(__file__).resolve().parents[1]
    declaration = read_python_declaration(candidate)
    assert set(declaration.requirements) == {
        'numpy==2.5.4', 'onnxruntime==1.31.0', 'tokenizers==0.23.3',
        'lancedb==0.40.0', 'pyarrow==26.0.0'}
    assert declaration.pyproject == candidate / 'pyproject.toml'
