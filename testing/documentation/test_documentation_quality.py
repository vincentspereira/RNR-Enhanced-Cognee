"""
RNR Enhanced Cognee Documentation Testing Framework

This module provides comprehensive documentation testing capabilities for the RNR Enhanced Cognee
Multi-Agent System, including API documentation accuracy, code documentation validation,
user guide testing, installation documentation validation, and knowledge base quality testing.

Coverage Target: 1% of total test coverage
Category: Documentation Testing (Advanced Testing - Phase 3)
"""

import pytest
import asyncio
import json
import time
import re
import ast
import inspect
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
from pathlib import Path
import logging
import yaml
import markdown
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Documentation Testing Markers
pytest.mark.documentation = pytest.mark.documentation
pytest.mark.api_docs = pytest.mark.api_docs
pytest.mark.code_docs = pytest.mark.code_docs
pytest.mark.user_guides = pytest.mark.user_guides
pytest.mark.installation = pytest.mark.installation
pytest.mark.knowledge_base = pytest.mark.knowledge_base


class DocumentationType(Enum):
    """Types of documentation to test"""
    API_DOCUMENTATION = "api_documentation"
    CODE_DOCUMENTATION = "code_documentation"
    USER_GUIDES = "user_guides"
    INSTALLATION_GUIDES = "installation_guides"
    TUTORIALS = "tutorials"
    KNOWLEDGE_BASE = "knowledge_base"
    CHANGELOGS = "changelogs"
    README = "readme"


@dataclass
class DocumentationTest:
    """Represents a documentation test case"""
    test_id: str
    name: str
    documentation_type: DocumentationType
    file_path: str
    test_type: str
    expected_content: List[str]
    validation_rules: Dict[str, Any]
    automated_check: bool = True
    manual_review_required: bool = False


@dataclass
class DocumentationMetrics:
    """Documentation quality metrics"""
    file_path: str
    total_words: int = 0
    total_sections: int = 0
    code_examples: int = 0
    images_diagrams: int = 0
    links_external: int = 0
    links_internal: int = 0
    readability_score: float = 0.0
    completeness_score: float = 0.0
    last_updated: Optional[datetime] = None


class DocumentationTestFramework:
    """Comprehensive documentation testing framework"""

    def __init__(self):
        self.test_results = {}
        self.documentation_metrics = {}
        self.broken_links = set()
        self.outdated_content = []
        self.coverage_gaps = []

    def parse_markdown(self, file_path: str) -> Dict[str, Any]:
        """Parse markdown file and extract structure"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse markdown to HTML
            html = markdown.markdown(content, extensions=['codehilite', 'toc', 'tables'])
            soup = BeautifulSoup(html, 'html.parser')

            # Extract structure
            structure = {
                "raw_content": content,
                "html_content": html,
                "headings": [],
                "code_blocks": [],
                "links": [],
                "images": [],
                "tables": [],
                "lists": [],
                "word_count": len(content.split()),
                "character_count": len(content)
            }

            # Extract headings
            for h1, h2, h3, h4, h5, h6 in [
                soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            ]:
                structure["headings"].append({
                    "level": int(h1.name[1]),
                    "text": h1.get_text().strip(),
                    "id": h1.get('id', '')
                })

            # Extract code blocks
            for code in soup.find_all(['pre', 'code']):
                structure["code_blocks"].append({
                    "type": code.name,
                    "content": code.get_text(),
                    "language": code.get('class', [''])[0] if code.get('class') else ''
                })

            # Extract links
            for a in soup.find_all('a', href=True):
                structure["links"].append({
                    "url": a['href'],
                    "text": a.get_text(),
                    "external": a['href'].startswith('http')
                })

            # Extract images
            for img in soup.find_all('img', src=True):
                structure["images"].append({
                    "src": img['src'],
                    "alt": img.get('alt', ''),
                    "title": img.get('title', '')
                })

            # Extract tables
            for table in soup.find_all('table'):
                structure["tables"].append({
                    "rows": len(table.find_all('tr')),
                    "headers": [th.get_text() for th in table.find_all('th')]
                })

            return structure

        except Exception as e:
            logger.error(f"Error parsing markdown file {file_path}: {str(e)}")
            return {}

    def analyze_code_documentation(self, file_path: str) -> Dict[str, Any]:
        """Analyze Python file for documentation quality"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            # Parse AST
            tree = ast.parse(source_code)

            analysis = {
                "file_path": file_path,
                "total_lines": len(source_code.splitlines()),
                "docstring_lines": 0,
                "functions": [],
                "classes": [],
                "modules": [],
                "comments": [],
                "docstring_coverage": 0.0,
                "type_hints": 0
            }

            # Extract docstrings and comments
            docstrings = []
            comments = []

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "has_docstring": ast.get_docstring(node) is not None,
                        "docstring": ast.get_docstring(node),
                        "args": len(node.args.args),
                        "return_annotation": node.returns is not None
                    }
                    analysis["functions"].append(func_info)
                    if func_info["has_docstring"]:
                        docstrings.append(ast.get_docstring(node))

                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "has_docstring": ast.get_docstring(node) is not None,
                        "docstring": ast.get_docstring(node),
                        "methods": len([n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))])
                    }
                    analysis["classes"].append(class_info)
                    if class_info["has_docstring"]:
                        docstrings.append(ast.get_docstring(node))

                elif isinstance(node, ast.Module):
                    module_docstring = ast.get_docstring(node)
                    if module_docstring:
                        analysis["modules"].append({
                            "docstring": module_docstring,
                            "length": len(module_docstring.splitlines())
                        })

                # Count type hints
                if isinstance(node, ast.AnnAssign):
                    analysis["type_hints"] += 1

            # Count comments (simple heuristic)
            comment_pattern = r'#.*$'
            comments = re.findall(comment_pattern, source_code, re.MULTILINE)
            analysis["comments"] = [c.strip() for c in comments if c.strip()]

            # Calculate docstring coverage
            total_docstring_targets = len(analysis["functions"]) + len(analysis["classes"])
            documented_targets = sum(1 for f in analysis["functions"] if f["has_docstring"]) + \
                                sum(1 for c in analysis["classes"] if c["has_docstring"])

            if total_docstring_targets > 0:
                analysis["docstring_coverage"] = documented_targets / total_docstring_targets

            # Count docstring lines
            for docstring in docstrings:
                if docstring:
                    analysis["docstring_lines"] += len(docstring.splitlines())

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing code documentation in {file_path}: {str(e)}")
            return {}

    def validate_api_documentation(self, api_spec_path: str) -> Dict[str, Any]:
        """Validate API specification documentation"""
        try:
            with open(api_spec_path, 'r', encoding='utf-8') as f:
                if api_spec_path.endswith('.yaml') or api_spec_path.endswith('.yml'):
                    api_spec = yaml.safe_load(f)
                else:
                    api_spec = json.load(f)

            validation = {
                "spec_version": api_spec.get("openapi", "Unknown"),
                "api_version": api_spec.get("info", {}).get("version", "Unknown"),
                "title": api_spec.get("info", {}).get("title", "Unknown"),
                "total_endpoints": 0,
                "documented_endpoints": 0,
                "endpoints_missing_descriptions": [],
                "missing_request_bodies": [],
                "missing_responses": [],
                "security_schemes": [],
                "components": []
            }

            # Validate endpoints
            if "paths" in api_spec:
                for path, path_item in api_spec["paths"].items():
                    for method, operation in path_item.items():
                        if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                            validation["total_endpoints"] += 1

                            # Check for description
                            if not operation.get("description") and not operation.get("summary"):
                                validation["endpoints_missing_descriptions"].append(f"{method.upper()} {path}")
                            else:
                                validation["documented_endpoints"] += 1

                            # Check request body for POST/PUT
                            if method.upper() in ["POST", "PUT"] and "requestBody" not in operation:
                                validation["missing_request_bodies"].append(f"{method.upper()} {path}")

                            # Check responses
                            if "responses" not in operation or not operation["responses"]:
                                validation["missing_responses"].append(f"{method.upper()} {path}")

            # Validate security schemes
            if "components" in api_spec and "securitySchemes" in api_spec["components"]:
                validation["security_schemes"] = list(api_spec["components"]["securitySchemes"].keys())

            # Validate components
            if "components" in api_spec:
                for component_type, components in api_spec["components"].items():
                    if isinstance(components, dict):
                        validation["components"].extend([f"{component_type}.{name}" for name in components.keys()])

            # Calculate documentation completeness
            if validation["total_endpoints"] > 0:
                validation["documentation_completeness"] = validation["documented_endpoints"] / validation["total_endpoints"]
            else:
                validation["documentation_completeness"] = 0.0

            return validation

        except Exception as e:
            logger.error(f"Error validating API documentation in {api_spec_path}: {str(e)}")
            return {}

    def check_link_validity(self, doc_structure: Dict[str, Any], base_path: str) -> List[str]:
        """Check if links in documentation are valid"""
        broken_links = []

        for link in doc_structure.get("links", []):
            url = link["url"]

            if url.startswith("#"):
                # Internal anchor link
                anchor = url[1:]
                if not any(h["id"] == anchor for h in doc_structure.get("headings", [])):
                    broken_links.append(f"Broken anchor: {url}")

            elif url.startswith("http"):
                # External link - would need actual HTTP request to validate
                # For testing purposes, just check format
                if not re.match(r'^https?://', url):
                    broken_links.append(f"Invalid external link format: {url}")

            else:
                # Internal file link
                file_path = Path(base_path) / url
                if not file_path.exists():
                    broken_links.append(f"Broken file link: {url}")

        # Check image links
        for image in doc_structure.get("images", []):
            src = image["src"]
            if not src.startswith("http"):
                file_path = Path(base_path) / src
                if not file_path.exists():
                    broken_links.append(f"Broken image link: {src}")

        return broken_links

    def calculate_readability_score(self, content: str) -> float:
        """Calculate basic readability score"""
        # Simplified readability calculation
        sentences = len(re.findall(r'[.!?]+', content))
        words = len(content.split())
        syllables = sum(len(re.findall(r'[aeiouAEIOU]+', word)) for word in content.split())

        if sentences == 0 or words == 0:
            return 0.0

        # Flesch Reading Ease Score (simplified)
        avg_sentence_length = words / sentences
        avg_syllables_per_word = syllables / words

        score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
        return max(0, min(100, score))

    def assess_documentation_completeness(self, doc_structure: Dict[str, Any],
                                        doc_type: str) -> float:
        """Assess documentation completeness based on type"""
        score = 0.0
        total_checks = 0

        # General checks
        if doc_structure.get("word_count", 0) > 50:
            score += 1
        total_checks += 1

        if doc_structure.get("headings"):
            score += 1
        total_checks += 1

        if doc_structure.get("links"):
            score += 1
        total_checks += 1

        # Type-specific checks
        if doc_type == "api_documentation":
            if doc_structure.get("code_blocks"):
                score += 1
            if doc_structure.get("tables"):
                score += 1
            total_checks += 2

        elif doc_type == "user_guide":
            if doc_structure.get("images"):
                score += 1
            if doc_structure.get("code_blocks"):
                score += 1
            total_checks += 2

        elif doc_type == "installation_guide":
            if "prerequisites" in str(doc_structure.get("headings", [])).lower():
                score += 1
            if "troubleshooting" in str(doc_structure.get("headings", [])).lower():
                score += 1
            total_checks += 2

        return score / total_checks if total_checks > 0 else 0.0


@pytest.fixture
def doc_framework():
    """Fixture for documentation testing framework"""
    return DocumentationTestFramework()


@pytest.fixture
def documentation_tests():
    """Fixture providing documentation test cases"""
    return [
        # API Documentation Tests
        DocumentationTest(
            test_id="DOC_API_001",
            name="API Specification Completeness",
            documentation_type=DocumentationType.API_DOCUMENTATION,
            file_path="docs/api/openapi.yaml",
            test_type="completeness_check",
            expected_content=["openapi", "info", "paths", "components"],
            validation_rules={
                "min_endpoints": 10,
                "min_description_length": 50,
                "require_request_bodies": True,
                "require_responses": True
            }
        ),

        DocumentationTest(
            test_id="DOC_API_002",
            name="API Examples and Samples",
            documentation_type=DocumentationType.API_DOCUMENTATION,
            file_path="docs/api/examples.md",
            test_type="example_validation",
            expected_content=["curl", "python", "javascript"],
            validation_rules={
                "min_examples": 5,
                "require_auth_examples": True,
                "require_error_examples": True
            }
        ),

        # Code Documentation Tests
        DocumentationTest(
            test_id="DOC_CODE_001",
            name="Python Code Documentation Coverage",
            documentation_type=DocumentationType.CODE_DOCUMENTATION,
            file_path="src/agents/",
            test_type="coverage_analysis",
            expected_content=["docstrings", "type_hints"],
            validation_rules={
                "min_docstring_coverage": 0.8,
                "require_class_docstrings": True,
                "require_function_docstrings": True
            }
        ),

        DocumentationTest(
            test_id="DOC_CODE_002",
            name="Type Hint Coverage",
            documentation_type=DocumentationType.CODE_DOCUMENTATION,
            file_path="src/memory/",
            test_type="type_hint_analysis",
            expected_content=["type_annotations"],
            validation_rules={
                "min_type_hint_coverage": 0.7,
                "require_return_types": True,
                "require_param_types": True
            }
        ),

        # User Guide Tests
        DocumentationTest(
            test_id="DOC_USER_001",
            name="Getting Started Guide",
            documentation_type=DocumentationType.USER_GUIDES,
            file_path="docs/user-guide/getting-started.md",
            test_type="completeness_check",
            expected_content=["installation", "configuration", "first_steps"],
            validation_rules={
                "min_word_count": 1000,
                "require_images": True,
                "require_code_examples": True,
                "require_troubleshooting": True
            }
        ),

        DocumentationTest(
            test_id="DOC_USER_002",
            name="Agent Management Guide",
            documentation_type=DocumentationType.USER_GUIDES,
            file_path="docs/user-guide/agent-management.md",
            test_type="workflow_validation",
            expected_content=["create_agent", "configure_agent", "monitor_agent"],
            validation_rules={
                "require_step_by_step": True,
                "require_screenshots": True,
                "require_best_practices": True
            }
        ),

        # Installation Guide Tests
        DocumentationTest(
            test_id="DOC_INSTALL_001",
            name="Installation Instructions",
            documentation_type=DocumentationType.INSTALLATION_GUIDES,
            file_path="docs/installation/docker.md",
            test_type="procedure_validation",
            expected_content=["prerequisites", "docker_compose", "environment_setup"],
            validation_rules={
                "require_version_info": True,
                "require_system_requirements": True,
                "require_verification_steps": True
            }
        ),

        DocumentationTest(
            test_id="DOC_INSTALL_002",
            name="Configuration Guide",
            documentation_type=DocumentationType.INSTALLATION_GUIDES,
            file_path="docs/installation/configuration.md",
            test_type="config_validation",
            expected_content=["environment_variables", "database_config", "security_config"],
            validation_rules={
                "require_examples": True,
                "require_default_values": True,
                "require_security_notes": True
            }
        ),

        # Knowledge Base Tests
        DocumentationTest(
            test_id="DOC_KB_001",
            name="FAQ Documentation",
            documentation_type=DocumentationType.KNOWLEDGE_BASE,
            file_path="docs/knowledge-base/faq.md",
            test_type="content_validation",
            expected_content=["common_questions", "troubleshooting", "best_practices"],
            validation_rules={
                "min_faqs": 20,
                "require_categorized": True,
                "require_search_terms": True
            }
        ),

        DocumentationTest(
            test_id="DOC_KB_002",
            name="Troubleshooting Guide",
            documentation_type=DocumentationType.KNOWLEDGE_BASE,
            file_path="docs/knowledge-base/troubleshooting.md",
            test_type="issue_validation",
            expected_content=["common_errors", "diagnostic_steps", "solutions"],
            validation_rules={
                "require_error_codes": True,
                "require_log_examples": True,
                "require_contact_info": True
            }
        )
    ]


class TestAPIDocumentation:
    """Test API documentation quality and accuracy"""

    @pytest.mark.documentation
    @pytest.mark.api_docs
    async def test_api_specification_completeness(self, doc_framework):
        """Test OpenAPI specification completeness"""
        api_spec_path = "docs/api/openapi.yaml"

        # Check if file exists (in real environment)
        # For demonstration, assume it exists and validate structure
        validation = doc_framework.validate_api_documentation(api_spec_path)

        # Validate basic OpenAPI structure
        assert validation.get("spec_version"), "OpenAPI version not specified"
        assert validation.get("title"), "API title not specified"
        assert validation.get("api_version"), "API version not specified"

        # Validate endpoint documentation
        assert validation.get("total_endpoints", 0) > 0, "No endpoints found in specification"

        # Validate documentation completeness
        completeness = validation.get("documentation_completeness", 0)
        assert completeness >= 0.8, f"API documentation completeness {completeness:.2%} below 80%"

        # Validate missing descriptions
        missing_descriptions = validation.get("endpoints_missing_descriptions", [])
        assert len(missing_descriptions) <= validation.get("total_endpoints", 0) * 0.1, \
            f"Too many endpoints missing descriptions: {len(missing_descriptions)}"

        # Validate security schemes
        security_schemes = validation.get("security_schemes", [])
        assert len(security_schemes) > 0, "No security schemes defined"

    @pytest.mark.documentation
    @pytest.mark.api_docs
    async def test_api_examples_validity(self, doc_framework):
        """Test API example validity and completeness"""
        examples_file = "docs/api/examples.md"

        # Parse examples file
        examples_structure = doc_framework.parse_markdown(examples_file)

        # Validate example content
        code_blocks = examples_structure.get("code_blocks", [])
        assert len(code_blocks) >= 5, f"Insufficient code examples: {len(code_blocks)}"

        # Check for different programming languages
        languages = set()
        for block in code_blocks:
            if block.get("language"):
                languages.add(block["language"])

        expected_languages = {"bash", "python", "javascript"}
        assert len(languages.intersection(expected_languages)) >= 2, \
            f"Missing language examples. Found: {languages}"

        # Validate curl examples
        curl_examples = [block for block in code_blocks if "curl" in block.get("content", "").lower()]
        assert len(curl_examples) >= 2, "Insufficient curl examples"

        # Validate authentication examples
        auth_content = examples_structure.get("raw_content", "").lower()
        assert "auth" in auth_content or "token" in auth_content or "bearer" in auth_content, \
            "Missing authentication examples"

    @pytest.mark.documentation
    @pytest.mark.api_docs
    async def test_api_response_documentation(self, doc_framework):
        """Test API response documentation accuracy"""
        api_spec_path = "docs/api/openapi.yaml"
        validation = doc_framework.validate_api_documentation(api_spec_path)

        # Check for response definitions
        missing_responses = validation.get("missing_responses", [])
        assert len(missing_responses) == 0, \
            f"Endpoints missing response documentation: {missing_responses}"

        # Validate component definitions
        components = validation.get("components", [])
        schema_components = [c for c in components if c.startswith("schemas.")]
        assert len(schema_components) > 0, "No schema definitions found"

        # Check for error response definitions
        error_schemas = [c for c in schema_components if "error" in c.lower()]
        assert len(error_schemas) > 0, "No error response schemas defined"

    @pytest.mark.documentation
    @pytest.mark.api_docs
    async def test_api_changelog_accuracy(self, doc_framework):
        """Test API changelog accuracy and completeness"""
        changelog_file = "CHANGELOG.md"

        # Parse changelog
        changelog_structure = doc_framework.parse_markdown(changelog_file)

        # Validate changelog structure
        headings = changelog_structure.get("headings", [])
        assert len(headings) >= 3, f"Insufficient changelog sections: {len(headings)}"

        # Check for version entries
        version_pattern = r'\d+\.\d+\.\d+'
        content = changelog_structure.get("raw_content", "")
        versions = re.findall(version_pattern, content)
        assert len(versions) >= 3, f"Insufficient version entries: {len(versions)}"

        # Validate change types
        change_types = ["added", "changed", "deprecated", "removed", "fixed", "security"]
        found_types = [ct for ct in change_types if ct.lower() in content.lower()]
        assert len(found_types) >= 4, f"Insufficient change type categories: {found_types}"


class TestCodeDocumentation:
    """Test code documentation quality and coverage"""

    @pytest.mark.documentation
    @pytest.mark.code_docs
    async def test_python_docstring_coverage(self, doc_framework):
        """Test Python docstring coverage"""
        # Test key source files
        source_files = [
            "src/agents/ats/algorithmic_trading_system.py",
            "src/memory/postgresql_memory_store.py",
            "src/agent_memory_integration.py"
        ]

        total_functions = 0
        documented_functions = 0
        total_classes = 0
        documented_classes = 0

        for file_path in source_files:
            analysis = doc_framework.analyze_code_documentation(file_path)

            total_functions += len(analysis.get("functions", []))
            documented_functions += sum(1 for f in analysis.get("functions", []) if f["has_docstring"])

            total_classes += len(analysis.get("classes", []))
            documented_classes += sum(1 for c in analysis.get("classes", []) if c["has_docstring"])

        # Calculate coverage
        function_coverage = documented_functions / total_functions if total_functions > 0 else 0
        class_coverage = documented_classes / total_classes if total_classes > 0 else 0

        # Validate coverage thresholds
        assert function_coverage >= 0.8, \
            f"Function docstring coverage {function_coverage:.2%} below 80%"

        assert class_coverage >= 0.9, \
            f"Class docstring coverage {class_coverage:.2%} below 90%"

    @pytest.mark.documentation
    @pytest.mark.code_docs
    async def test_docstring_quality(self, doc_framework):
        """Test docstring quality and content"""
        source_file = "src/agents/ats/algorithmic_trading_system.py"
        analysis = doc_framework.analyze_code_documentation(source_file)

        # Check function docstrings
        for func in analysis.get("functions", []):
            if func["has_docstring"] and func["docstring"]:
                docstring = func["docstring"]

                # Validate docstring length
                assert len(docstring.split()) >= 10, \
                    f"Function {func['name']} docstring too short"

                # Validate docstring content
                assert any(word in docstring.lower() for word in ["param", "return", "raise", "args"]), \
                    f"Function {func['name']} docstring missing parameter/return documentation"

        # Check class docstrings
        for cls in analysis.get("classes", []):
            if cls["has_docstring"] and cls["docstring"]:
                docstring = cls["docstring"]

                # Validate class docstring length
                assert len(docstring.split()) >= 15, \
                    f"Class {cls['name']} docstring too short"

                # Validate class docstring content
                assert "class" in docstring.lower() or "purpose" in docstring.lower(), \
                    f"Class {cls['name']} docstring missing class description"

    @pytest.mark.documentation
    @pytest.mark.code_docs
    async def test_type_hint_coverage(self, doc_framework):
        """Test type hint annotation coverage"""
        source_files = [
            "src/memory/qdrant_memory_store.py",
            "src/agents/oma/orchestration_manager.py"
        ]

        total_parameters = 0
        typed_parameters = 0
        total_returns = 0
        typed_returns = 0

        for file_path in source_files:
            analysis = doc_framework.analyze_code_documentation(file_path)

            for func in analysis.get("functions", []):
                # Count parameters (simplified)
                total_parameters += func["args"]
                # Check return annotation
                total_returns += 1
                if func["return_annotation"]:
                    typed_returns += 1

            # Count type annotations from AST analysis
            type_hints = analysis.get("type_hints", 0)
            typed_parameters += min(type_hints, total_parameters)

        # Calculate coverage
        parameter_coverage = typed_parameters / total_parameters if total_parameters > 0 else 0
        return_coverage = typed_returns / total_returns if total_returns > 0 else 0

        # Validate type hint coverage
        assert parameter_coverage >= 0.7, \
            f"Parameter type hint coverage {parameter_coverage:.2%} below 70%"

        assert return_coverage >= 0.8, \
            f"Return type hint coverage {return_coverage:.2%} below 80%"

    @pytest.mark.documentation
    @pytest.mark.code_docs
    async def test_module_documentation(self, doc_framework):
        """Test module-level documentation"""
        source_files = [
            "src/__init__.py",
            "src/agents/__init__.py",
            "src/memory/__init__.py"
        ]

        for file_path in source_files:
            analysis = doc_framework.analyze_code_documentation(file_path)

            # Check for module docstrings
            modules = analysis.get("modules", [])
            assert len(modules) > 0, f"Module {file_path} missing module docstring"

            for module in modules:
                docstring = module.get("docstring", "")
                assert len(docstring.split()) >= 20, \
                    f"Module {file_path} docstring too short"

                # Validate module docstring content
                content_lower = docstring.lower()
                assert any(word in content_lower for word in ["package", "module", "contains", "provides"]), \
                    f"Module {file_path} docstring missing package description"


class TestUserGuides:
    """Test user guide documentation quality and usability"""

    @pytest.mark.documentation
    @pytest.mark.user_guides
    async def test_getting_started_guide(self, doc_framework):
        """Test getting started guide completeness"""
        guide_file = "docs/user-guide/getting-started.md"
        guide_structure = doc_framework.parse_markdown(guide_file)

        # Validate content requirements
        content = guide_structure.get("raw_content", "").lower()

        required_sections = [
            "installation", "setup", "configuration", "first_steps", "next_steps"
        ]

        for section in required_sections:
            assert section in content, \
                f"Getting started guide missing required section: {section}"

        # Validate word count
        word_count = guide_structure.get("word_count", 0)
        assert word_count >= 800, \
            f"Getting started guide too short: {word_count} words"

        # Validate code examples
        code_blocks = guide_structure.get("code_blocks", [])
        assert len(code_blocks) >= 5, \
            f"Getting started guide needs more code examples: {len(code_blocks)}"

        # Validate images/diagrams
        images = guide_structure.get("images", [])
        assert len(images) >= 2, \
            f"Getting started guide needs more images: {len(images)}"

        # Validate readability
        readability_score = doc_framework.calculate_readability_score(content)
        assert readability_score >= 30, \
            f"Getting started guide readability too low: {readability_score}"

    @pytest.mark.documentation
    @pytest.mark.user_guides
    async def test_user_guide_navigation(self, doc_framework):
        """Test user guide navigation and structure"""
        user_guide_dir = "docs/user-guide/"

        # Parse main user guide index
        index_file = f"{user_guide_dir}index.md"
        index_structure = doc_framework.parse_markdown(index_file)

        # Validate navigation structure
        headings = index_structure.get("headings", [])
        assert len([h for h in headings if h["level"] == 2]) >= 5, \
            "User guide index needs more main sections"

        # Validate internal links
        links = index_structure.get("links", [])
        internal_links = [link for link in links if not link["external"]]
        assert len(internal_links) >= 5, \
            "User guide needs more navigation links"

        # Check link validity
        broken_links = doc_framework.check_link_validity(index_structure, user_guide_dir)
        assert len(broken_links) == 0, \
            f"User guide has broken links: {broken_links}"

    @pytest.mark.documentation
    @pytest.mark.user_guides
    async def test_tutorial_quality(self, doc_framework):
        """Test tutorial documentation quality"""
        tutorial_files = [
            "docs/user-guide/tutorials/basic-usage.md",
            "docs/user-guide/tutorials/advanced-features.md"
        ]

        for tutorial_file in tutorial_files:
            tutorial_structure = doc_framework.parse_markdown(tutorial_file)

            # Validate tutorial structure
            headings = tutorial_structure.get("headings", [])
            assert len(headings) >= 4, \
                f"Tutorial {tutorial_file} needs more sections"

            # Check for step-by-step instructions
            content = tutorial_structure.get("raw_content", "").lower()
            step_indicators = ["step", "1.", "first", "then", "next", "finally"]
            step_count = sum(1 for indicator in step_indicators if indicator in content)
            assert step_count >= 3, \
                f"Tutorial {tutorial_file} lacks step-by-step format"

            # Validate code examples
            code_blocks = tutorial_structure.get("code_blocks", [])
            assert len(code_blocks) >= 3, \
                f"Tutorial {tutorial_file} needs more code examples"

            # Validate expected outcomes
            assert "expected" in content or "result" in content or "output" in content, \
                f"Tutorial {tutorial_file} missing expected results"

    @pytest.mark.documentation
    @pytest.mark.user_guides
    async def test_troubleshooting_guide(self, doc_framework):
        """Test troubleshooting guide effectiveness"""
        troubleshooting_file = "docs/user-guide/troubleshooting.md"
        ts_structure = doc_framework.parse_markdown(troubleshooting_file)

        # Validate common issues coverage
        content = ts_structure.get("raw_content", "").lower()

        common_issues = [
            "connection", "authentication", "performance", "memory", "error"
        ]

        covered_issues = [issue for issue in common_issues if issue in content]
        assert len(covered_issues) >= 4, \
            f"Troubleshooting guide covers insufficient issues: {covered_issues}"

        # Validate problem-solution format
        headings = ts_structure.get("headings", [])
        problem_headings = [h for h in headings if "error" in h["text"].lower() or "problem" in h["text"].lower()]
        assert len(problem_headings) >= 5, \
            "Troubleshooting guide needs more problem sections"

        # Validate solution clarity
        assert "solution" in content or "fix" in content or "resolve" in content, \
            "Troubleshooting guide missing clear solutions"

        # Validate code examples for fixes
        code_blocks = ts_structure.get("code_blocks", [])
        assert len(code_blocks) >= 3, \
            "Troubleshooting guide needs more code examples for fixes"


class TestInstallationGuides:
    """Test installation guide accuracy and completeness"""

    @pytest.mark.documentation
    @pytest.mark.installation
    async def test_installation_prerequisites(self, doc_framework):
        """Test installation guide prerequisites coverage"""
        install_file = "docs/installation/prerequisites.md"
        install_structure = doc_framework.parse_markdown(install_file)

        content = install_structure.get("raw_content", "").lower()

        # Validate system requirements coverage
        system_components = [
            "python", "docker", "memory", "disk", "cpu", "operating_system"
        ]

        covered_components = [comp for comp in system_components if comp.replace("_", "") in content.replace(" ", "")]
        assert len(covered_components) >= 5, \
            f"Prerequisites guide covers insufficient components: {covered_components}"

        # Validate version specifications
        version_pattern = r'\d+\.\d+'
        versions = re.findall(version_pattern, content)
        assert len(versions) >= 4, \
            f"Prerequisites guide missing version specifications: {len(versions)}"

        # Validate compatibility information
        assert "compatibility" in content or "support" in content, \
            "Prerequisites guide missing compatibility information"

    @pytest.mark.documentation
    @pytest.mark.installation
    async def test_docker_installation_guide(self, doc_framework):
        """Test Docker installation guide accuracy"""
        docker_file = "docs/installation/docker.md"
        docker_structure = doc_framework.parse_markdown(docker_file)

        content = docker_structure.get("raw_content", "").lower()

        # Validate Docker-specific content
        docker_components = [
            "docker_compose", "container", "image", "volume", "network", "environment"
        ]

        covered_components = [comp for comp in docker_components if comp.replace("_", "") in content.replace(" ", "")]
        assert len(covered_components) >= 5, \
            f"Docker guide covers insufficient components: {covered_components}"

        # Validate docker-compose examples
        assert "docker-compose.yml" in content or "compose" in content, \
            "Docker guide missing docker-compose examples"

        # Validate environment configuration
        assert "environment" in content and "variable" in content, \
            "Docker guide missing environment configuration"

        # Validate verification steps
        assert "verify" in content or "test" in content or "check" in content, \
            "Docker guide missing verification steps"

    @pytest.mark.documentation
    @pytest.mark.installation
    async def test_configuration_guide(self, doc_framework):
        """Test configuration guide completeness"""
        config_file = "docs/installation/configuration.md"
        config_structure = doc_framework.parse_markdown(config_file)

        content = config_structure.get("raw_content", "").lower()

        # Validate configuration categories
        config_categories = [
            "database", "security", "logging", "performance", "authentication"
        ]

        covered_categories = [cat for cat in config_categories if cat in content]
        assert len(covered_categories) >= 4, \
            f"Configuration guide covers insufficient categories: {covered_categories}"

        # Validate example configurations
        code_blocks = config_structure.get("code_blocks", [])
        config_examples = [block for block in code_blocks if any(
            key in block.get("content", "").lower()
            for key in ["env", "yaml", "json", "config"]
        )]
        assert len(config_examples) >= 3, \
            "Configuration guide needs more example configurations"

        # Validate default values
        assert "default" in content, \
            "Configuration guide missing default values"

        # Validate security considerations
        security_content = ["secret", "key", "password", "encrypt", "secure"]
        security_found = any(sec in content for sec in security_content)
        assert security_found, \
            "Configuration guide missing security considerations"

    @pytest.mark.documentation
    @pytest.mark.installation
    async def test_installation_verification(self, doc_framework):
        """Test installation verification procedures"""
        verify_file = "docs/installation/verification.md"
        verify_structure = doc_framework.parse_markdown(verify_file)

        content = verify_structure.get("raw_content", "").lower()

        # Validate health checks
        health_indicators = [
            "health_check", "status", "ping", "test", "verify", "diagnostic"
        ]

        health_found = [indicator for indicator in health_indicators if indicator.replace("_", "") in content.replace(" ", "")]
        assert len(health_found) >= 3, \
            f"Verification guide covers insufficient health checks: {health_found}"

        # Validate service checks
        services = ["api", "database", "memory", "agent"]
        service_checks = [service for service in services if service in content]
        assert len(service_checks) >= 3, \
            f"Verification guide covers insufficient services: {service_checks}"

        # Validate troubleshooting integration
        assert "troubleshoot" in content or "issue" in content or "problem" in content, \
            "Verification guide should reference troubleshooting"

        # Validate success indicators
        success_indicators = ["success", "ready", "running", "active", "healthy"]
        success_found = any(indicator in content for indicator in success_indicators)
        assert success_found, \
            "Verification guide missing success indicators"


class TestKnowledgeBase:
    """Test knowledge base documentation quality and usefulness"""

    @pytest.mark.documentation
    @pytest.mark.knowledge_base
    async def test_faq_completeness(self, doc_framework):
        """Test FAQ completeness and organization"""
        faq_file = "docs/knowledge-base/faq.md"
        faq_structure = doc_framework.parse_markdown(faq_file)

        # Validate FAQ structure
        headings = faq_structure.get("headings", [])
        question_headings = [h for h in headings if h["level"] <= 2]

        assert len(question_headings) >= 15, \
            f"FAQ needs more questions: {len(question_headings)}"

        # Validate FAQ categorization
        content = faq_structure.get("raw_content", "").lower()
        categories = [
            "general", "installation", "configuration", "agents", "memory",
            "performance", "troubleshooting", "security"
        ]

        found_categories = [cat for cat in categories if cat in content]
        assert len(found_categories) >= 5, \
            f"FAQ covers insufficient categories: {found_categories}"

        # Validate answer quality
        answers = []
        current_answer = []
        in_answer = False

        for line in faq_structure.get("raw_content", "").split('\n'):
            if line.startswith('#'):
                if current_answer and in_answer:
                    answers.append('\n'.join(current_answer))
                    current_answer = []
                in_answer = line.startswith('##')  # Questions are typically H2
            elif in_answer:
                current_answer.append(line)

        if current_answer:
            answers.append('\n'.join(current_answer))

        # Validate answer length
        detailed_answers = [ans for ans in answers if len(ans.split()) >= 20]
        assert len(detailed_answers) >= len(answers) * 0.7, \
            "FAQ needs more detailed answers"

    @pytest.mark.documentation
    @pytest.mark.knowledge_base
    async def test_troubleshooting_guide_quality(self, doc_framework):
        """Test troubleshooting guide quality and effectiveness"""
        ts_file = "docs/knowledge-base/troubleshooting.md"
        ts_structure = doc_framework.parse_markdown(ts_file)

        content = ts_structure.get("raw_content", "").lower()

        # Validate error coverage
        error_types = [
            "connection", "timeout", "memory", "permission", "configuration",
            "performance", "authentication", "dependency"
        ]

        covered_errors = [error for error in error_types if error in content]
        assert len(covered_errors) >= 6, \
            f"Troubleshooting guide covers insufficient error types: {covered_errors}"

        # Validate diagnostic procedures
        diagnostic_indicators = [
            "diagnose", "check", "verify", "test", "identify", "log", "debug"
        ]

        diagnostic_found = [indicator for indicator in diagnostic_indicators if indicator in content]
        assert len(diagnostic_found) >= 5, \
            f"Troubleshooting guide insufficient diagnostic procedures: {diagnostic_found}"

        # Validate solution clarity
        solution_indicators = [
            "solution", "fix", "resolve", "correct", "address", "remedy"
        ]

        solution_found = any(indicator in content for indicator in solution_indicators)
        assert solution_found, \
            "Troubleshooting guide should clearly present solutions"

        # Validate code examples for fixes
        code_blocks = ts_structure.get("code_blocks", [])
        fix_examples = [block for block in code_blocks if any(
            keyword in block.get("content", "").lower()
            for keyword in ["fix", "config", "command", "script"]
        )]
        assert len(fix_examples) >= 3, \
            "Troubleshooting guide needs more fix examples"

    @pytest.mark.documentation
    @pytest.mark.knowledge_base
    async def test_best_practices_documentation(self, doc_framework):
        """Test best practices documentation quality"""
        bp_file = "docs/knowledge-base/best-practices.md"
        bp_structure = doc_framework.parse_markdown(bp_file)

        content = bp_structure.get("raw_content", "").lower()

        # Validate practice categories
        practice_areas = [
            "security", "performance", "scalability", "maintenance",
            "monitoring", "deployment", "development"
        ]

        covered_areas = [area for area in practice_areas if area in content]
        assert len(covered_areas) >= 5, \
            f"Best practices guide covers insufficient areas: {covered_areas}"

        # Validate actionable advice
        actionable_indicators = [
            "should", "must", "recommend", "avoid", "ensure", "implement", "configure"
        ]

        actionable_count = sum(1 for indicator in actionable_indicators if indicator in content)
        assert actionable_count >= 20, \
            "Best practices guide needs more actionable advice"

        # Validate examples and implementation guidance
        code_blocks = bp_structure.get("code_blocks", [])
        assert len(code_blocks) >= 5, \
            "Best practices guide needs more implementation examples"

        # Validate anti-patterns coverage
        anti_pattern_indicators = ["avoid", "don't", "never", "warning", "caution", "anti-pattern"]
        anti_patterns_found = any(indicator in content for indicator in anti_pattern_indicators)
        assert anti_patterns_found, \
            "Best practices guide should cover anti-patterns"

    @pytest.mark.documentation
    @pytest.mark.knowledge_base
    async def test_glossary_completeness(self, doc_framework):
        """Test glossary completeness and accuracy"""
        glossary_file = "docs/knowledge-base/glossary.md"
        glossary_structure = doc_framework.parse_markdown(glossary_file)

        # Validate glossary structure
        headings = glossary_structure.get("headings", [])
        term_headings = [h for h in headings if h["level"] <= 3]

        assert len(term_headings) >= 25, \
            f"Glossary needs more terms: {len(term_headings)}"

        # Validate term definitions
        definitions = []
        current_definition = []
        in_definition = False

        for line in glossary_structure.get("raw_content", "").split('\n'):
            if line.startswith('#'):
                if current_definition and in_definition:
                    definitions.append('\n'.join(current_definition))
                    current_definition = []
                in_definition = line.startswith('##') or line.startswith('###')
            elif in_definition:
                current_definition.append(line)

        if current_definition:
            definitions.append('\n'.join(current_definition))

        # Validate definition quality
        detailed_definitions = [defn for defn in definitions if len(defn.split()) >= 15]
        assert len(detailed_definitions) >= len(definitions) * 0.8, \
            "Glossary needs more detailed definitions"

        # Validate cross-references
        content = glossary_structure.get("raw_content", "")
        cross_reference_pattern = r'\[.*?\]\(#.*?\)'
        cross_references = re.findall(cross_reference_pattern, content)
        assert len(cross_references) >= 10, \
            "Glossary needs more cross-references"

        # Validate term relevance
        technical_terms = [
            "agent", "memory", "cognee", "ats", "oma", "smc", "postgresql",
            "qdrant", "neo4j", "redis", "embedding", "vector", "semantic"
        ]

        term_content = content.lower()
        found_terms = [term for term in technical_terms if term in term_content]
        assert len(found_terms) >= 8, \
            f"Glossary covers insufficient technical terms: {found_terms}"


# Integration with existing test framework
pytest_plugins = []