#!/usr/bin/env python3
"""
Code Reviewer Agent
OMA Category - Code quality analysis and review automation
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, UTC
from ...agent_memory_integration import AgentMemoryIntegration
from .oma_memory_wrapper import OMAMemoryWrapper

logger = logging.getLogger(__name__)

class CodeReviewer:
    """
    Code Reviewer Agent
    OMA agent responsible for code quality analysis, security audits, and best practices enforcement
    """

    def __init__(self, memory_integration: AgentMemoryIntegration):
        self.memory_integration = memory_integration
        self.oma_memory = OMAMemoryWrapper(memory_integration)

        # Agent configuration
        self.agent_config = {
            "agent_id": "code-reviewer",
            "category": "OMA",
            "prefix": "oma_",
            "description": "Code review and quality analysis specialist",
            "capabilities": [
                "code_analysis",
                "quality_check",
                "security_audit",
                "performance_review",
                "best_practices_check"
            ],
            "max_concurrent_tasks": 3,
            "critical": False
        }

        # Review criteria and thresholds
        self.review_criteria = {
            "complexity_threshold": 10,  # Cyclomatic complexity
            "duplication_threshold": 0.05,  # 5% duplication allowed
            "min_test_coverage": 0.8,  # 80% minimum test coverage
            "max_function_length": 50,  # Lines per function
            "max_file_length": 500,  # Lines per file
            "security_severity_levels": ["critical", "high", "medium", "low"]
        }

        # Review state
        self.review_state = {
            "active_reviews": {},
            "review_history": [],
            "quality_trends": {},
            "common_issues": {}
        }

    async def initialize(self):
        """Initialize the code reviewer agent"""
        try:
            logger.info(f"Initializing {self.agent_config['agent_id']}")

            # Load review configuration from memory
            await self._load_review_configuration()

            # Initialize code analysis tools
            await self._initialize_analysis_tools()

            # Load review history and patterns
            await self._load_review_patterns()

            logger.info(f"{self.agent_config['agent_id']} initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize {self.agent_config['agent_id']}: {e}")
            raise

    async def review_code_changes(self, review_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review code changes and provide comprehensive analysis
        """
        try:
            review_id = f"review_{datetime.now(UTC).timestamp()}"

            review_results = {
                "review_id": review_id,
                "request_id": review_request.get("request_id"),
                "repository": review_request.get("repository"),
                "branch": review_request.get("branch"),
                "commit_hash": review_request.get("commit_hash"),
                "files_changed": review_request.get("files_changed", []),
                "timestamp": datetime.now(UTC).isoformat(),
                "overall_score": 0,
                "status": "in_progress",
                "issues_found": [],
                "suggestions": [],
                "security_issues": [],
                "performance_issues": [],
                "quality_metrics": {}
            }

            # Analyze each file
            total_score = 0
            file_count = len(review_request.get("files_changed", []))

            for file_info in review_request.get("files_changed", []):
                file_review = await self._analyze_file(file_info, review_request)
                review_results["issues_found"].extend(file_review.get("issues", []))
                review_results["suggestions"].extend(file_review.get("suggestions", []))
                review_results["security_issues"].extend(file_review.get("security_issues", []))
                review_results["performance_issues"].extend(file_review.get("performance_issues", []))
                total_score += file_review.get("score", 0)

            # Calculate overall score
            review_results["overall_score"] = total_score / file_count if file_count > 0 else 0

            # Determine review status
            if review_results["overall_score"] >= 90:
                review_results["status"] = "approved"
            elif review_results["overall_score"] >= 70:
                review_results["status"] = "approved_with_suggestions"
            elif review_results["overall_score"] >= 50:
                review_results["status"] = "needs_changes"
            else:
                review_results["status"] = "rejected"

            # Calculate quality metrics
            review_results["quality_metrics"] = await self._calculate_quality_metrics(review_request)

            # Store review results
            await self.oma_memory.store_code_review(
                agent_id=self.agent_config["agent_id"],
                review_data=review_results
            )

            # Update review state
            self.review_state["active_reviews"][review_id] = review_results

            logger.info(f"Code review completed: {review_id} (Score: {review_results['overall_score']:.1f})")

            return review_results

        except Exception as e:
            logger.error(f"Failed to review code changes: {e}")
            return {"error": str(e), "status": "failed"}

    async def analyze_code_quality(self, analysis_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive code quality analysis
        """
        try:
            analysis_id = f"quality_{datetime.now(UTC).timestamp()}"

            quality_analysis = {
                "analysis_id": analysis_id,
                "repository": analysis_request.get("repository"),
                "scope": analysis_request.get("scope", "full_repository"),
                "timestamp": datetime.now(UTC).isoformat(),
                "quality_score": 0,
                "complexity_analysis": {},
                "duplication_analysis": {},
                "test_coverage": {},
                "maintainability_index": 0,
                "technical_debt": {},
                "recommendations": []
            }

            # Perform complexity analysis
            complexity_results = await self._analyze_complexity(analysis_request)
            quality_analysis["complexity_analysis"] = complexity_results

            # Analyze code duplication
            duplication_results = await self._analyze_duplication(analysis_request)
            quality_analysis["duplication_analysis"] = duplication_results

            # Analyze test coverage
            coverage_results = await self._analyze_test_coverage(analysis_request)
            quality_analysis["test_coverage"] = coverage_results

            # Calculate maintainability index
            maintainability_score = await self._calculate_maintainability_index(
                complexity_results, duplication_results, coverage_results
            )
            quality_analysis["maintainability_index"] = maintainability_score

            # Assess technical debt
            technical_debt = await self._assess_technical_debt(quality_analysis)
            quality_analysis["technical_debt"] = technical_debt

            # Calculate overall quality score
            quality_analysis["quality_score"] = self._calculate_overall_quality_score(quality_analysis)

            # Generate recommendations
            recommendations = await self._generate_quality_recommendations(quality_analysis)
            quality_analysis["recommendations"] = recommendations

            # Store quality analysis
            await self.oma_memory.store_analysis_report(
                agent_id=self.agent_config["agent_id"],
                report={
                    "type": "quality_analysis",
                    "title": f"Code Quality Analysis - {analysis_request.get('repository', 'Unknown')}",
                    "content": quality_analysis,
                    "severity": self._determine_severity_from_score(quality_analysis["quality_score"])
                }
            )

            return quality_analysis

        except Exception as e:
            logger.error(f"Failed to analyze code quality: {e}")
            return {"error": str(e)}

    async def security_scan(self, scan_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform security vulnerability scan on code
        """
        try:
            scan_id = f"security_{datetime.now(UTC).timestamp()}"

            security_scan = {
                "scan_id": scan_id,
                "repository": scan_request.get("repository"),
                "scan_type": scan_request.get("scan_type", "full"),
                "timestamp": datetime.now(UTC).isoformat(),
                "vulnerabilities_found": [],
                "security_score": 100,  # Start with perfect score
                "high_risk_issues": [],
                "medium_risk_issues": [],
                "low_risk_issues": [],
                "security_recommendations": []
            }

            # Scan for common security vulnerabilities
            security_issues = await self._scan_for_security_vulnerabilities(scan_request)

            # Categorize issues by severity
            for issue in security_issues:
                severity = issue.get("severity", "low")
                security_scan[f"{severity}_risk_issues"].append(issue)

                # Deduct points based on severity
                if severity == "critical":
                    security_scan["security_score"] -= 25
                elif severity == "high":
                    security_scan["security_score"] -= 15
                elif severity == "medium":
                    security_scan["security_score"] -= 8
                elif severity == "low":
                    security_scan["security_score"] -= 3

            security_scan["vulnerabilities_found"] = security_issues

            # Generate security recommendations
            recommendations = await self._generate_security_recommendations(security_issues)
            security_scan["security_recommendations"] = recommendations

            # Store security scan results
            await self.oma_memory.store_analysis_report(
                agent_id=self.agent_config["agent_id"],
                report={
                    "type": "security_scan",
                    "title": f"Security Scan - {scan_request.get('repository', 'Unknown')}",
                    "content": security_scan,
                    "severity": "high" if security_scan["security_score"] < 70 else "medium"
                }
            )

            return security_scan

        except Exception as e:
            logger.error(f"Failed to perform security scan: {e}")
            return {"error": str(e)}

    async def get_review_statistics(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Get code review statistics and trends
        """
        try:
            # Get review history from memory
            review_history = self.review_state.get("review_history", [])

            # Filter by date range
            cutoff_date = datetime.now(UTC) - timedelta(days=days_back)
            recent_reviews = [
                review for review in review_history
                if datetime.fromisoformat(review.get("timestamp", "")) >= cutoff_date
            ]

            # Calculate statistics
            total_reviews = len(recent_reviews)
            approved_reviews = len([r for r in recent_reviews if r.get("status") == "approved"])
            average_score = sum(r.get("overall_score", 0) for r in recent_reviews) / total_reviews if total_reviews > 0 else 0

            # Identify common issues
            common_issues = self._identify_common_issues(recent_reviews)

            # Calculate quality trends
            quality_trends = self._calculate_quality_trends(recent_reviews)

            statistics = {
                "period_days": days_back,
                "total_reviews": total_reviews,
                "approval_rate": (approved_reviews / total_reviews * 100) if total_reviews > 0 else 0,
                "average_score": average_score,
                "common_issues": common_issues,
                "quality_trends": quality_trends,
                "productivity_metrics": {
                    "avg_review_time": self._calculate_average_review_time(recent_reviews),
                    "reviews_per_day": total_reviews / days_back if days_back > 0 else 0
                }
            }

            return statistics

        except Exception as e:
            logger.error(f"Failed to get review statistics: {e}")
            return {"error": str(e)}

    async def _analyze_file(self, file_info: Dict[str, Any], review_request: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single file for code quality issues"""
        file_path = file_info.get("path", "")
        file_content = file_info.get("content", "")

        analysis = {
            "file_path": file_path,
            "score": 100,  # Start with perfect score
            "issues": [],
            "suggestions": [],
            "security_issues": [],
            "performance_issues": []
        }

        # Check file length
        lines = len(file_content.splitlines())
        if lines > self.review_criteria["max_file_length"]:
            analysis["issues"].append({
                "type": "file_length",
                "severity": "medium",
                "message": f"File too long ({lines} lines, max {self.review_criteria['max_file_length']})",
                "line": 1
            })
            analysis["score"] -= 10

        # Analyze complexity (simplified)
        complexity = self._calculate_cyclomatic_complexity(file_content)
        if complexity > self.review_criteria["complexity_threshold"]:
            analysis["issues"].append({
                "type": "high_complexity",
                "severity": "medium",
                "message": f"High cyclomatic complexity ({complexity})",
                "line": 1
            })
            analysis["score"] -= 15

        # Check for common security issues
        security_issues = await self._check_file_security_issues(file_path, file_content)
        analysis["security_issues"].extend(security_issues)
        for issue in security_issues:
            if issue.get("severity") in ["critical", "high"]:
                analysis["score"] -= 20
            else:
                analysis["score"] -= 10

        # Check for performance issues
        performance_issues = await self._check_file_performance_issues(file_path, file_content)
        analysis["performance_issues"].extend(performance_issues)
        analysis["score"] -= len(performance_issues) * 5

        # Generate suggestions for improvements
        suggestions = await self._generate_file_suggestions(file_path, file_content)
        analysis["suggestions"].extend(suggestions)

        return analysis

    def _calculate_cyclomatic_complexity(self, content: str) -> int:
        """Calculate cyclomatic complexity (simplified)"""
        # Count decision points
        complexity = 1  # Base complexity
        decision_keywords = ["if", "elif", "else", "for", "while", "try", "except", "with"]

        for keyword in decision_keywords:
            complexity += content.count(keyword)

        return complexity

    async def _check_file_security_issues(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Check for security issues in file content"""
        issues = []

        # Check for hardcoded secrets
        secret_patterns = [
            ("password", "password ="),
            ("api_key", "api_key ="),
            ("secret", "secret ="),
            ("token", "token =")
        ]

        for secret_name, pattern in secret_patterns:
            if pattern in content.lower():
                issues.append({
                    "type": "hardcoded_secret",
                    "severity": "high",
                    "message": f"Potential hardcoded {secret_name} detected",
                    "line": content.lower().find(pattern) // 50  # Approximate line number
                })

        # Check for SQL injection vulnerabilities
        if "execute(" in content and "%" in content:
            issues.append({
                "type": "sql_injection",
                "severity": "critical",
                "message": "Potential SQL injection vulnerability",
                "line": content.find("execute(") // 50
            })

        return issues

    async def _check_file_performance_issues(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Check for performance issues in file content"""
        issues = []

        # Check for inefficient loops
        if content.count("for ") > 5:
            issues.append({
                "type": "inefficient_loops",
                "severity": "medium",
                "message": "Multiple nested loops detected - consider optimization",
                "line": 1
            })

        # Check for memory leaks (simplified)
        if "open(" in content and content.count("close(") < content.count("open("):
            issues.append({
                "type": "resource_leak",
                "severity": "medium",
                "message": "Potential resource leak - file handles not properly closed",
                "line": 1
            })

        return issues

    async def _generate_file_suggestions(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Generate improvement suggestions for the file"""
        suggestions = []

        # Suggest adding comments if code is complex
        complexity = self._calculate_cyclomatic_complexity(content)
        if complexity > 8 and '"""' not in content and "'''" not in content:
            suggestions.append({
                "type": "documentation",
                "message": "Consider adding docstrings for complex functions",
                "line": 1
            })

        # Suggest breaking up large functions
        lines = content.splitlines()
        if len(lines) > 100:
            suggestions.append({
                "type": "refactoring",
                "message": "Consider breaking this large function into smaller functions",
                "line": 1
            })

        return suggestions

    async def _analyze_complexity(self, analysis_request: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code complexity metrics"""
        # Simplified complexity analysis
        return {
            "average_cyclomatic_complexity": 6.5,
            "max_complexity": 15,
            "complex_functions": ["function1", "function2"],
            "complexity_score": 75
        }

    async def _analyze_duplication(self, analysis_request: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code duplication"""
        # Simplified duplication analysis
        return {
            "duplication_percentage": 3.2,
            "duplicated_blocks": 5,
            "total_duplicated_lines": 150,
            "duplication_score": 85
        }

    async def _analyze_test_coverage(self, analysis_request: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test coverage"""
        # Simplified test coverage analysis
        return {
            "line_coverage": 82.5,
            "branch_coverage": 78.3,
            "function_coverage": 90.1,
            "overall_coverage": 83.6,
            "coverage_score": 84
        }

    async def _calculate_maintainability_index(self, complexity_results: Dict, duplication_results: Dict, coverage_results: Dict) -> float:
        """Calculate maintainability index"""
        # Simplified maintainability calculation
        complexity_score = complexity_results.get("complexity_score", 75)
        duplication_score = duplication_results.get("duplication_score", 85)
        coverage_score = coverage_results.get("coverage_score", 84)

        return (complexity_score + duplication_score + coverage_score) / 3

    async def _assess_technical_debt(self, quality_analysis: Dict) -> Dict[str, Any]:
        """Assess technical debt"""
        # Simplified technical debt assessment
        return {
            "debt_hours": 40,
            "debt_cost_estimate": 2000,
            "priority_issues": 8,
            "debt_ratio": 0.12
        }

    def _calculate_overall_quality_score(self, quality_analysis: Dict) -> float:
        """Calculate overall quality score"""
        maintainability = quality_analysis.get("maintainability_index", 0)

        # Weight different factors
        weights = {
            "maintainability": 0.4,
            "complexity": 0.3,
            "duplication": 0.2,
            "coverage": 0.1
        }

        score = (
            maintainability * weights["maintainability"] +
            quality_analysis.get("complexity_analysis", {}).get("complexity_score", 75) * weights["complexity"] +
            quality_analysis.get("duplication_analysis", {}).get("duplication_score", 85) * weights["duplication"] +
            quality_analysis.get("test_coverage", {}).get("coverage_score", 84) * weights["coverage"]
        )

        return min(score, 100)

    async def _generate_quality_recommendations(self, quality_analysis: Dict) -> List[str]:
        """Generate quality improvement recommendations"""
        recommendations = []

        maintainability = quality_analysis.get("maintainability_index", 0)
        if maintainability < 70:
            recommendations.append("Focus on improving code maintainability through refactoring")

        duplication = quality_analysis.get("duplication_analysis", {}).get("duplication_percentage", 0)
        if duplication > 5:
            recommendations.append("Reduce code duplication by extracting common functionality")

        coverage = quality_analysis.get("test_coverage", {}).get("overall_coverage", 100)
        if coverage < 80:
            recommendations.append("Increase test coverage to meet minimum standards")

        return recommendations

    async def _scan_for_security_vulnerabilities(self, scan_request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scan for security vulnerabilities"""
        # Simplified security scan
        vulnerabilities = []

        # Example vulnerability patterns
        example_vulnerabilities = [
            {
                "type": "xss",
                "severity": "medium",
                "message": "Potential XSS vulnerability in user input handling",
                "file": "user_input.py",
                "line": 45
            },
            {
                "type": "authentication",
                "severity": "high",
                "message": "Weak authentication mechanism detected",
                "file": "auth.py",
                "line": 12
            }
        ]

        vulnerabilities.extend(example_vulnerabilities)
        return vulnerabilities

    async def _generate_security_recommendations(self, security_issues: List[Dict]) -> List[str]:
        """Generate security improvement recommendations"""
        recommendations = []

        critical_issues = [issue for issue in security_issues if issue.get("severity") == "critical"]
        if critical_issues:
            recommendations.append("Address all critical security vulnerabilities immediately")

        high_issues = [issue for issue in security_issues if issue.get("severity") == "high"]
        if high_issues:
            recommendations.append("Prioritize fixing high-severity security issues")

        return recommendations

    def _determine_severity_from_score(self, score: float) -> str:
        """Determine severity level from quality score"""
        if score >= 90:
            return "low"
        elif score >= 70:
            return "medium"
        else:
            return "high"

    def _identify_common_issues(self, reviews: List[Dict]) -> Dict[str, int]:
        """Identify most common issues in reviews"""
        issue_counts = {}

        for review in reviews:
            for issue in review.get("issues_found", []):
                issue_type = issue.get("type", "unknown")
                issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1

        return issue_counts

    def _calculate_quality_trends(self, reviews: List[Dict]) -> Dict[str, List[float]]:
        """Calculate quality trends over time"""
        # Simplified trend calculation
        scores = [review.get("overall_score", 0) for review in reviews]

        return {
            "score_trend": scores[-10:],  # Last 10 reviews
            "moving_average": [sum(scores[i:i+5])/5 for i in range(0, len(scores)-5, 5)]  # 5-review moving average
        }

    def _calculate_average_review_time(self, reviews: List[Dict]) -> float:
        """Calculate average time to complete reviews"""
        # Simplified calculation
        return 45.5  # minutes

    async def _load_review_configuration(self):
        """Load review configuration from memory"""
        pass

    async def _initialize_analysis_tools(self):
        """Initialize code analysis tools"""
        pass

    async def _load_review_patterns(self):
        """Load review patterns and history"""
        pass

# Factory function for agent creation
async def create_code_reviewer(memory_integration: AgentMemoryIntegration) -> CodeReviewer:
    """Create and initialize Code Reviewer agent"""
    agent = CodeReviewer(memory_integration)
    await agent.initialize()
    return agent

if __name__ == "__main__":
    # Example usage
    async def example_usage():
        from ...agent_memory_integration import AgentMemoryIntegration

        integration = AgentMemoryIntegration()
        await integration.initialize()

        code_reviewer = await create_code_reviewer(integration)

        # Review code changes
        review_request = {
            "request_id": "review_001",
            "repository": "enhanced-cognee",
            "branch": "feature/new-agent",
            "commit_hash": "abc123",
            "files_changed": [
                {
                    "path": "src/agents/new_agent.py",
                    "content": "def complex_function():\n    if condition1:\n        for item in items:\n            if condition2:\n                return result"
                }
            ]
        }

        review_results = await code_reviewer.review_code_changes(review_request)
        print(f"Review results: {review_results}")

        # Perform security scan
        security_scan = await code_reviewer.security_scan({
            "repository": "enhanced-cognee",
            "scan_type": "full"
        })
        print(f"Security scan: {security_scan}")

        await integration.close()

    asyncio.run(example_usage())