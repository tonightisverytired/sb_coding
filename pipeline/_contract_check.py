"""Structural contract checker — compares spec interface contracts against actual code.

Usage:
  python pipeline/_contract_check.py --spec <spec.md> --source <src_dir>

Template dependency: Python only. Uses the ``ast`` module to parse Python source files.
For TypeScript/Go/Rust projects, this tool is a no-op — use the manual L2 contract comparison
checklist in self_verify/SELF_VERIFY.md instead.

Parses the spec for interface contract blocks (§2.x sections with type signatures),
extracts actual function/class signatures from source via AST, and reports mismatches.

Covers ~80% of L2 checks (structural): function exists, param count, type annotations present.
Does NOT cover semantic checks (return value correctness, business logic).
"""

import ast
import os
import re
import sys
from dataclasses import dataclass, field


@dataclass
class ContractSymbol:
    """A symbol expected by the spec."""
    name: str
    kind: str  # "function" | "class" | "method" | "enum"
    params: list[str] = field(default_factory=list)  # param names from spec
    return_type: str = ""  # expected return type hint from spec


@dataclass
class ActualSymbol:
    """A symbol found in source code."""
    name: str
    kind: str
    params: list[str] = field(default_factory=list)
    return_type: str = ""
    file: str = ""
    line: int = 0


def parse_spec_contracts(spec_path: str) -> list[ContractSymbol]:
    """Extract interface contracts from a spec file.

    Looks for patterns like:
      func_name(param1: type, param2: type) -> ReturnType
      ClassName:
        method1(...) -> ...

    Methods indented under a ClassName: block are automatically prefixed
    with the class name (e.g. ``TransactionService.authorize``), matching
    the namespace-qualified names that ``extract_source_symbols`` produces.
    This prevents false positives from same-named methods in different classes.
    """
    symbols: list[ContractSymbol] = []
    if not os.path.exists(spec_path):
        print(f"[contract_check] Spec file not found: {spec_path}")
        return symbols

    with open(spec_path, "r", encoding="utf-8") as f:
        text = f.read()

    func_pattern = re.compile(
        r"^(\s*)(\w+)\s*\(([^)]*)\)\s*(?:->\s*(\S+(?:\s*\|\s*\S+)*))?",
        re.MULTILINE,
    )
    class_pattern = re.compile(r"^(\w+):\s*$", re.MULTILINE)

    # Build a set of class declaration line numbers for context tracking
    class_lines: dict[int, str] = {}  # line_number -> class_name
    for cm in class_pattern.finditer(text):
        cls_name = cm.group(1)
        if cls_name[0].islower():
            continue
        line_num = text[: cm.start()].count("\n")
        class_lines[line_num] = cls_name

    for match in func_pattern.finditer(text):
        name = match.group(2)
        if name in ("def", "class", "if", "for", "while", "with", "import", "from", "raise", "return"):
            continue

        indent = match.group(1)
        params_str = match.group(3).strip()
        params = [p.split(":")[0].strip() for p in params_str.split(",") if p.strip()] if params_str else []
        ret = match.group(4) or ""
        match_line = text[: match.start()].count("\n")

        # Determine namespace: if indented and preceded by a class declaration,
        # prefix the method name with the class name.
        is_indented = len(indent) >= 2
        qualified_name = name
        kind = "function"

        if is_indented:
            # Find the nearest preceding class declaration
            closest_class_line = max((ln for ln in class_lines if ln < match_line), default=-1)
            if closest_class_line >= 0:
                qualified_name = f"{class_lines[closest_class_line]}.{name}"
                kind = "method"

        symbols.append(ContractSymbol(name=qualified_name, kind=kind, params=params, return_type=ret.strip()))

    return symbols


def extract_source_symbols(src_dir: str) -> list[ActualSymbol]:
    """Extract all function/class/method signatures from Python source files."""
    symbols: list[ActualSymbol] = []

    for root, _dirs, files in os.walk(src_dir):
        for fname in files:
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=fpath)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    params = [a.arg for a in node.args.args]
                    ret = ast.unparse(node.returns) if node.returns else ""
                    symbols.append(ActualSymbol(
                        name=node.name, kind="function", params=params,
                        return_type=ret, file=fpath, line=node.lineno,
                    ))
                elif isinstance(node, ast.ClassDef):
                    symbols.append(ActualSymbol(
                        name=node.name, kind="class", file=fpath, line=node.lineno,
                    ))
                    # Also extract methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            params = [a.arg for a in item.args.args if a.arg != "self"]
                            ret = ast.unparse(item.returns) if item.returns else ""
                            symbols.append(ActualSymbol(
                                name=f"{node.name}.{item.name}", kind="method",
                                params=params, return_type=ret, file=fpath, line=item.lineno,
                            ))

    return symbols


def parse_gherkin_specs(spec_path: str) -> list[ContractSymbol]:
    """Extract HTTP endpoints from Gherkin-format OpenSpec specs.

    Looks for patterns like:
      #### Scenario: Successful login
      - WHEN POST /login with {...}
      - THEN return 200 with {"token": "..."}

    This is a fallback for specs without type-annotated interface contracts.
    """
    symbols: list[ContractSymbol] = []
    if not os.path.exists(spec_path):
        return symbols

    with open(spec_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Match: WHEN (POST|GET|PUT|DELETE|PATCH) /path
    endpoint_pattern = re.compile(
        r"WHEN\s+(GET|POST|PUT|DELETE|PATCH)\s+(/\S+)",
        re.IGNORECASE,
    )
    seen: set[str] = set()
    for match in endpoint_pattern.finditer(text):
        method = match.group(1).upper()
        path = match.group(2)
        key = f"{method} {path}"
        if key in seen:
            continue
        seen.add(key)
        symbols.append(ContractSymbol(
            name=key, kind="endpoint",
            params=[method, path], return_type="",
        ))

    return symbols


def extract_fastapi_endpoints(src_dir: str) -> list[ActualSymbol]:
    """Extract FastAPI route endpoints from source files via regex.

    Matches patterns like:
      @router.get("/products")
      @router.post("/checkout")
    """
    symbols: list[ActualSymbol] = []
    route_pattern = re.compile(
        r"@(\w+)\.(get|post|put|delete|patch)\s*\(\s*[\"']([^\"']+)[\"']",
    )

    for root, _dirs, files in os.walk(src_dir):
        for fname in files:
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue

            for match in route_pattern.finditer(content):
                method = match.group(2).upper()
                path = match.group(3)
                key = f"{method} {path}"
                symbols.append(ActualSymbol(
                    name=key, kind="endpoint", file=fpath, line=0,
                ))

    return symbols


def run_check(spec_path: str, src_dir: str) -> tuple[list[str], list[str]]:
    """Run the contract check. Returns (passes, failures)."""
    expected = parse_spec_contracts(spec_path)
    actual = extract_source_symbols(src_dir)

    actual_map: dict[str, ActualSymbol] = {s.name: s for s in actual}
    passes: list[str] = []
    failures: list[str] = []

    for exp in expected:
        if exp.name not in actual_map:
            failures.append(f"MISSING: {exp.kind} '{exp.name}' — defined in spec but not found in code")
            continue

        act = actual_map[exp.name]

        # Check kind
        if exp.kind != "function" and exp.kind != act.kind:
            failures.append(
                f"TYPE_MISMATCH: '{exp.name}' — spec says {exp.kind}, code has {act.kind} "
                f"({act.file}:{act.line})"
            )
            continue

        # Check param count (if spec has params defined)
        # Strip 'self' from actual params — spec never includes self, AST always does for methods
        act_params = [p for p in act.params if p != "self"]
        if exp.params and len(exp.params) != len(act_params):
            failures.append(
                f"PARAM_COUNT: '{exp.name}' — spec expects {len(exp.params)} params ({exp.params}), "
                f"code has {len(act_params)} ({act_params}) ({act.file}:{act.line})"
            )
            continue

        # Check return type presence
        if exp.return_type and not act.return_type:
            failures.append(
                f"RETURN_TYPE_MISSING: '{exp.name}' — spec expects '-> {exp.return_type}', "
                f"code has no return type annotation ({act.file}:{act.line})"
            )
            continue

        passes.append(f"OK: {exp.kind} '{exp.name}' ({act.file}:{act.line})")

    return passes, failures


if __name__ == "__main__":
    spec_path = sys.argv[sys.argv.index("--spec") + 1] if "--spec" in sys.argv else ""
    src_dir = sys.argv[sys.argv.index("--source") + 1] if "--source" in sys.argv else "src/"

    if not spec_path:
        print("Usage: python pipeline/_contract_check.py --spec <spec.md> --source <src_dir>")
        sys.exit(1)

    print(f"[contract_check] Spec: {spec_path}")
    print(f"[contract_check] Source: {src_dir}")
    print()

    # Phase 1: Type-signature contracts (works with PROJECT_SPEC.md style specs)
    passes, failures = run_check(spec_path, src_dir)
    total_symbols = len(passes) + len(failures)

    # Phase 2: Gherkin fallback — if type parser found few/no contracts, try endpoint extraction
    if total_symbols < 3:
        print(f"[contract_check] Type parser found only {total_symbols} contracts. Trying Gherkin fallback...")
        print()
        gherkin_expected = parse_gherkin_specs(spec_path)
        gherkin_actual = extract_fastapi_endpoints(src_dir)

        if gherkin_expected:
            actual_names = {s.name for s in gherkin_actual}
            for exp in gherkin_expected:
                if exp.name in actual_names:
                    passes.append(f"OK: endpoint '{exp.name}' (found in code)")
                else:
                    failures.append(f"MISSING: endpoint '{exp.name}' — defined in spec but no matching route found")
        else:
            print("[contract_check] Gherkin fallback found no endpoints either. Spec may use an unsupported format.")

    if passes:
        print(f"PASSED ({len(passes)}):")
        for p in passes:
            print(f"  {p}")

    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    else:
        print(f"All {len(passes)} contracts structurally verified.")
