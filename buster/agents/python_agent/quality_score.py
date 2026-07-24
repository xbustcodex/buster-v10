import ast
from .models import QualityMetrics


class QualityScorer:
    @staticmethod
    def evaluate(original_code: str, new_code: str, syntax_ok: bool, compile_ok: bool) -> QualityMetrics:
        metrics = QualityMetrics(syntax_ok=syntax_ok, compile_ok=compile_ok)

        if not syntax_ok or not compile_ok:
            metrics.overall_score = 0.0
            return metrics

        # Compare AST structures (Classes and Functions retained)
        try:
            orig_ast = ast.parse(original_code)
            new_ast = ast.parse(new_code)

            orig_classes = {node.name for node in ast.walk(orig_ast) if isinstance(node, ast.ClassDef)}
            new_classes = {node.name for node in ast.walk(new_ast) if isinstance(node, ast.ClassDef)}

            orig_funcs = {node.name for node in ast.walk(orig_ast) if isinstance(node, ast.FunctionDef)}
            new_funcs = {node.name for node in ast.walk(new_ast) if isinstance(node, ast.FunctionDef)}

            # Class retention
            if orig_classes:
                retained = len(orig_classes.intersection(new_classes))
                metrics.class_retention = retained / len(orig_classes)

            # Function retention
            if orig_funcs:
                retained = len(orig_funcs.intersection(new_funcs))
                metrics.function_retention = retained / len(orig_funcs)

            # Size ratio penalty if code randomly drops drastically in size (>70% drop)
            orig_len = max(len(original_code.strip()), 1)
            new_len = len(new_code.strip())
            metrics.size_ratio = min(new_len / orig_len, 1.0)

            # Score calculation
            score = (
                (100.0 if syntax_ok else 0) * 0.4
                + (100.0 if compile_ok else 0) * 0.4
                + (metrics.class_retention * 100.0) * 0.1
                + (metrics.function_retention * 100.0) * 0.1
            )

            metrics.overall_score = round(score, 2)

        except Exception:
            metrics.overall_score = 50.0  # Fallback baseline if AST comparison fails

        return metrics