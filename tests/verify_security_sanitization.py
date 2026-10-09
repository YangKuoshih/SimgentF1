"""
F1 Simgent - Security & Credential Sanitization Audit
Verifies that:
1. Zero secrets, API keys, or service account files are tracked in git.
2. Checks are limited to supported key patterns, not a complete history audit.
3. .gitignore and .dockerignore strictly exclude sensitive patterns.
4. .env.example contains only clean placeholder templates.
5. Source code contains zero hardcoded API keys.
"""

import os
import re
import subprocess
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestSecuritySanitization(unittest.TestCase):

    def test_no_secret_files_tracked_in_git(self):
        """Verifies no credentials, .env, or keys are tracked by git."""
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True
        )
        tracked_files = result.stdout.splitlines()
        forbidden_patterns = [
            r"^\.env($|\..*)",
            r".*\.pem$",
            r".*\.key$",
            r".*service[_-]?account.*\.json$",
            r".*credentials.*\.json$",
            r".*client_secret.*\.json$",
            r".*sa-key.*\.json$"
        ]
        leaks = []
        for f in tracked_files:
            if f == ".env.example":
                continue
            for pattern in forbidden_patterns:
                if re.match(pattern, f, re.IGNORECASE):
                    leaks.append(f)

        self.assertEqual(leaks, [], f"Forbidden secret files tracked in git: {leaks}")

    def test_gitignore_contains_critical_rules(self):
        """Verifies that .gitignore blocks .env, credentials, and service accounts."""
        gitignore_path = os.path.join(PROJECT_ROOT, ".gitignore")
        self.assertTrue(os.path.exists(gitignore_path), ".gitignore must exist")
        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_rules = [
            ".env",
            "!.env.example",
            "*.pem",
            "*.key",
            "*-sa-key*.json",
            "*credentials*.json"
        ]
        for rule in required_rules:
            self.assertIn(rule, content, f".gitignore is missing required rule: {rule}")

    def test_dockerignore_contains_critical_rules(self):
        """Verifies that .dockerignore prevents secrets from entering container builds."""
        dockerignore_path = os.path.join(PROJECT_ROOT, ".dockerignore")
        self.assertTrue(os.path.exists(dockerignore_path), ".dockerignore must exist")
        with open(dockerignore_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_rules = [
            ".env*",
            ".git/",
            "*.pem",
            "*.key",
            "*credentials*.json"
        ]
        for rule in required_rules:
            self.assertIn(rule, content, f".dockerignore is missing required rule: {rule}")

    def test_env_example_has_no_real_secrets(self):
        """Verifies .env.example contains only empty values and no real keys."""
        example_path = os.path.join(PROJECT_ROOT, ".env.example")
        self.assertTrue(os.path.exists(example_path), ".env.example must exist")
        with open(example_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertNotIn("AIzaSy", content)
        self.assertNotIn("gsk_", content)
        self.assertNotIn("sk-", content)
        self.assertIn("GROQ_API_KEY=", content)
        self.assertIn("GEMINI_API_KEY=", content)

    def test_source_code_has_no_hardcoded_keys(self):
        """Scans python, js, and html files for accidental hardcoded API keys."""
        key_patterns = [
            re.compile(r"gsk_[a-zA-Z0-9]{20,}"),
            re.compile(r"AIzaSy[a-zA-Z0-9_-]{33}"),
            re.compile(r"sk-[a-zA-Z0-9]{20,}"),
            re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
            re.compile(r"01208F-[0-9A-Z]{6}-[0-9A-Z]{6}")
        ]
        violations = []
        tracked = subprocess.run(
            ["git", "ls-files", "-z"], cwd=PROJECT_ROOT,
            capture_output=True, text=True, check=True
        ).stdout.split("\0")
        for relative_path in tracked:
            if not relative_path.endswith((".py", ".js", ".html", ".sh", ".json", ".md")):
                continue
            fpath = os.path.join(PROJECT_ROOT, relative_path)
            with open(fpath, "r", encoding="utf-8", errors="ignore") as source:
                content = source.read()
            if any(pattern.search(content) for pattern in key_patterns):
                # Report the file, never a fragment of a potential credential.
                violations.append(relative_path)

        self.assertEqual(violations, [], f"Hardcoded API key patterns found: {violations}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
