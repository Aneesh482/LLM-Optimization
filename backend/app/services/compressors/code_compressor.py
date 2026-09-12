"""Code Compressor for LLM Context Optimization.

Features
--------
1. Language Detection: Identifies Python, JS/TS, Go, Java, Rust, C/C++, SQL, etc.
2. Python AST-based Analysis:
   - Preserves import statements, module docstrings, class definitions, method signatures,
     decorators, and type annotations.
   - Condenses long method implementations into structure-preserving stubs.
3. Multi-Language Regex Structure Extractor:
   - Preserves imports/exports, type/interface definitions, function headers, and class structures.
   - Strips non-essential whitespace, heavy comment blocks, and repetitive boilerplate.
4. Compression Metrics:
   - Measures token savings, byte reduction, language, and preserved symbols.
"""

from __future__ import annotations

import ast
import re
from typing import Any, Optional

from app.services.compressors.base import BaseCompressor, CompressionResult
from app.services.token_analyzer import estimate_tokens


class CodeCompressor(BaseCompressor):
    """Structure-preserving source code compressor."""

    DEFAULT_MIN_LINES_TO_COMPRESS = 15

    def content_type(self) -> str:
        return "code"

    def compress(
        self,
        content: str,
        *,
        language: Optional[str] = None,
        min_lines: Optional[int] = None,
        preserve_docstrings: bool = True,
        skeleton_only: bool = False,
        **options: Any,
    ) -> CompressionResult:
        """Compress source code while preserving signatures, classes, imports, and structure."""
        raw_text = content.strip()
        original_size = len(content.encode("utf-8"))
        tokens_before = estimate_tokens(content)

        if not raw_text:
            return self._build_result(
                original=content,
                compressed="",
                original_size=original_size,
                metadata={"strategy": "empty", "language": "unknown"},
            )

        detected_lang = (language or self._detect_language(raw_text)).lower()
        threshold = min_lines or self.DEFAULT_MIN_LINES_TO_COMPRESS
        line_count = len(raw_text.splitlines())

        # Baseline: basic comment/whitespace cleanup
        minified_verbatim = self._clean_whitespace_and_comments(raw_text, detected_lang)
        minified_bytes = len(minified_verbatim.encode("utf-8"))

        compressed_candidate: Optional[str] = None
        candidate_meta: dict[str, Any] = {}

        if line_count >= threshold or skeleton_only:
            if detected_lang == "python":
                compressed_candidate, candidate_meta = self._compress_python(
                    raw_text,
                    preserve_docstrings=preserve_docstrings,
                )
            else:
                compressed_candidate, candidate_meta = self._compress_generic_code(
                    raw_text,
                    detected_lang,
                )

        # Fallback to minified if candidate is larger or not produced
        if compressed_candidate:
            candidate_bytes = len(compressed_candidate.encode("utf-8"))
            if candidate_bytes < minified_bytes:
                return self._build_result(
                    original=content,
                    compressed=compressed_candidate,
                    original_size=original_size,
                    metadata=candidate_meta,
                )

        return self._build_result(
            original=content,
            compressed=minified_verbatim,
            original_size=original_size,
            metadata={
                "strategy": "code_minification",
                "language": detected_lang,
                "original_lines": line_count,
            },
        )

    # ── Python AST Compressor ───────────────────────────────────────────

    def _compress_python(
        self,
        code: str,
        preserve_docstrings: bool = True,
    ) -> tuple[str, dict[str, Any]]:
        """Extract high-level AST skeleton (imports, classes, functions, signatures)."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return self._compress_generic_code(code, "python")

        classes_found = 0
        functions_found = 0
        imports_found = 0
        output_lines: list[str] = []

        # Module docstring
        docstring = ast.get_docstring(tree)
        if docstring and preserve_docstrings:
            first_line = docstring.strip().split("\n")[0][:120]
            output_lines.append(f'"""{first_line}"""\n')

        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports_found += 1
                output_lines.append(ast.unparse(node))

            elif isinstance(node, ast.ClassDef):
                classes_found += 1
                class_lines = self._unparse_class_skeleton(node, preserve_docstrings)
                output_lines.append(class_lines)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions_found += 1
                fn_lines = self._unparse_func_skeleton(node, preserve_docstrings, indent="")
                output_lines.append(fn_lines)

            elif isinstance(node, ast.Assign):
                # Preserve top-level constants / type aliases (e.g. ALL_CAPS or __all__)
                for target in node.targets:
                    if isinstance(target, ast.Name) and (target.id.isupper() or target.id.startswith("__")):
                        output_lines.append(ast.unparse(node))
                        break

        skeleton = "\n".join(output_lines)
        meta = {
            "strategy": "python_ast_skeleton",
            "language": "python",
            "imports_count": imports_found,
            "classes_count": classes_found,
            "functions_count": functions_found,
            "original_lines": len(code.splitlines()),
            "compressed_lines": len(skeleton.splitlines()),
        }
        return skeleton, meta

    def _unparse_class_skeleton(self, node: ast.ClassDef, preserve_docstrings: bool) -> str:
        """Render a class header with method stubs."""
        bases = [ast.unparse(b) for b in node.bases]
        bases_str = f"({', '.join(bases)})" if bases else ""
        lines = [f"\nclass {node.name}{bases_str}:"]

        doc = ast.get_docstring(node)
        if doc and preserve_docstrings:
            first_line = doc.strip().split("\n")[0][:100]
            lines.append(f'    """{first_line}"""')

        methods = 0
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods += 1
                lines.append(self._unparse_func_skeleton(item, preserve_docstrings, indent="    "))
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                lines.append(f"    {ast.unparse(item)}")

        if methods == 0 and len(lines) == 1:
            lines.append("    pass")

        return "\n".join(lines)

    def _unparse_func_skeleton(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        preserve_docstrings: bool,
        indent: str = "",
    ) -> str:
        """Render function signature with docstring and ellipsis stub."""
        prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
        args = ast.unparse(node.args)
        returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""

        # Decorators
        decor_lines = [f"{indent}@{ast.unparse(d)}" for d in node.decorator_list]
        sig = f"{indent}{prefix}{node.name}({args}){returns}:"
        
        body_lines = []
        doc = ast.get_docstring(node)
        if doc and preserve_docstrings:
            first_line = doc.strip().split("\n")[0][:100]
            body_lines.append(f'{indent}    """{first_line}"""')
        body_lines.append(f"{indent}    ...")

        all_lines = decor_lines + [sig] + body_lines
        return "\n".join(all_lines)

    # ── Generic Multi-Language Compressor ───────────────────────────────

    def _compress_generic_code(
        self,
        code: str,
        language: str,
    ) -> tuple[str, dict[str, Any]]:
        """Extract imports, interfaces, structs, and function signatures using regex."""
        lines = code.splitlines()
        output_lines: list[str] = []
        functions_found = 0
        types_found = 0

        # Patterns matching function/class signatures in JS, TS, Java, Go, Rust, C++
        sig_pattern = re.compile(
            r"^\s*(export\s+|public\s+|private\s+|protected\s+|static\s+|async\s+|fn\s+|func\s+|def\s+|class\s+|interface\s+|struct\s+|type\s+|enum\s+)",
            re.MULTILINE,
        )
        import_pattern = re.compile(r"^\s*(import|from|require|include|use|package)\s+", re.MULTILINE)

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if import_pattern.match(stripped):
                output_lines.append(stripped)
                continue

            if sig_pattern.match(stripped):
                functions_found += 1
                if stripped.endswith("{") or stripped.endswith(":"):
                    output_lines.append(line)
                    output_lines.append("    // ... implementation ...")
                    output_lines.append("}")
                else:
                    output_lines.append(stripped)

        if not output_lines:
            output_lines = [self._clean_whitespace_and_comments(code, language)]

        skeleton = "\n".join(output_lines)
        meta = {
            "strategy": "generic_regex_skeleton",
            "language": language,
            "functions_and_types_count": functions_found,
            "original_lines": len(lines),
            "compressed_lines": len(output_lines),
        }
        return skeleton, meta

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _detect_language(code: str) -> str:
        """Detect source language from keywords."""
        if re.search(r"^\s*(def|class|import|from\s+\w+\s+import)\s+", code, re.MULTILINE):
            return "python"
        if re.search(r"\b(const|let|var|function|interface|export\s+default)\b", code):
            return "javascript"
        if re.search(r"\b(func\s+\w+\(|package\s+\w+)\b", code):
            return "go"
        if re.search(r"\b(fn\s+\w+|impl\s+|pub\s+struct)\b", code):
            return "rust"
        if re.search(r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE TABLE)\b", code, re.IGNORECASE):
            return "sql"
        if re.search(r"\b(public\s+class|private\s+void|System\.out\.println)\b", code):
            return "java"
        return "text"

    @staticmethod
    def _clean_whitespace_and_comments(code: str, language: str) -> str:
        """Strip single-line comments and unnecessary blank lines."""
        lines = code.splitlines()
        cleaned: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if language == "python" and stripped.startswith("#"):
                continue
            if language in ("javascript", "typescript", "java", "go", "rust", "c", "cpp") and stripped.startswith("//"):
                continue
            cleaned.append(line)
        return "\n".join(cleaned)

    @staticmethod
    def _build_result(
        original: str,
        compressed: str,
        original_size: int,
        metadata: dict[str, Any],
    ) -> CompressionResult:
        compressed_bytes = len(compressed.encode("utf-8"))
        tokens_before = estimate_tokens(original)
        tokens_after = estimate_tokens(compressed)
        ratio = round(compressed_bytes / max(1, original_size), 4)

        return CompressionResult(
            original_content=original,
            compressed_content=compressed,
            original_size=original_size,
            compressed_size=compressed_bytes,
            compression_ratio=ratio,
            estimated_tokens_before=tokens_before,
            estimated_tokens_after=tokens_after,
            estimated_tokens_saved=max(0, tokens_before - tokens_after),
            content_type="code",
            metadata=metadata,
        )
