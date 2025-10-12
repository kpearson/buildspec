"""Unit tests for cli.utils.__init__.py module exports."""

import importlib


class TestReviewTargetsImport:
    """Test that ReviewTargets can be imported from cli.utils."""

    def test_review_targets_importable_from_cli_utils(self):
        """Verify that ReviewTargets can be imported from cli.utils."""
        from cli.utils import ReviewTargets

        # Verify it's the correct class
        assert ReviewTargets.__name__ == "ReviewTargets"
        assert hasattr(ReviewTargets, "__dataclass_fields__")

    def test_review_targets_has_correct_fields(self):
        """Verify ReviewTargets has all expected fields."""
        from cli.utils import ReviewTargets

        expected_fields = {
            "primary_file",
            "additional_files",
            "editable_directories",
            "artifacts_dir",
            "updates_doc_name",
            "log_file_name",
            "error_file_name",
            "epic_name",
            "reviewer_session_id",
            "review_type",
        }
        actual_fields = set(ReviewTargets.__dataclass_fields__.keys())
        assert actual_fields == expected_fields


class TestApplyReviewFeedbackImport:
    """Test that apply_review_feedback can be imported from cli.utils."""

    def test_apply_review_feedback_importable_from_cli_utils(self):
        """Verify that apply_review_feedback can be imported."""
        from cli.utils import apply_review_feedback

        # Verify it's a callable function
        assert callable(apply_review_feedback)
        assert apply_review_feedback.__name__ == "apply_review_feedback"

    def test_apply_review_feedback_has_correct_signature(self):
        """Verify apply_review_feedback has expected parameters."""
        import inspect

        from cli.utils import apply_review_feedback

        sig = inspect.signature(apply_review_feedback)
        param_names = list(sig.parameters.keys())

        expected_params = [
            "review_artifact_path",
            "builder_session_id",
            "context",
            "targets",
            "console",
        ]
        assert param_names == expected_params


class TestExistingImports:
    """Test that existing imports still work correctly."""

    def test_path_resolution_error_importable(self):
        """Verify PathResolutionError is still importable."""
        from cli.utils import PathResolutionError

        # Verify it's an exception class
        assert issubclass(PathResolutionError, Exception)

    def test_resolve_file_argument_importable(self):
        """Verify resolve_file_argument is still importable."""
        from cli.utils import resolve_file_argument

        # Verify it's a callable function
        assert callable(resolve_file_argument)
        assert resolve_file_argument.__name__ == "resolve_file_argument"


class TestAllList:
    """Test the __all__ list exports."""

    def test_all_list_includes_new_exports(self):
        """Verify __all__ includes ReviewTargets and apply_review_feedback."""
        from cli import utils

        assert "ReviewTargets" in utils.__all__
        assert "apply_review_feedback" in utils.__all__

    def test_all_list_includes_existing_exports(self):
        """Verify __all__ includes existing PathResolutionError exports."""
        from cli import utils

        assert "PathResolutionError" in utils.__all__
        assert "resolve_file_argument" in utils.__all__

    def test_all_list_length(self):
        """Verify __all__ has exactly 4 exports."""
        from cli import utils

        assert len(utils.__all__) == 4

    def test_all_list_alphabetically_sorted(self):
        """Verify __all__ list is alphabetically sorted."""
        from cli import utils

        expected_order = [
            "PathResolutionError",
            "ReviewTargets",
            "apply_review_feedback",
            "resolve_file_argument",
        ]
        assert utils.__all__ == expected_order


class TestStarImport:
    """Test that star imports work correctly."""

    def test_star_import_includes_all_public_exports(self):
        """Verify 'from cli.utils import *' includes all public exports."""
        # Create a clean namespace to test star import
        test_namespace = {}
        exec("from cli.utils import *", test_namespace)

        # Check all expected exports are present
        assert "ReviewTargets" in test_namespace
        assert "apply_review_feedback" in test_namespace
        assert "PathResolutionError" in test_namespace
        assert "resolve_file_argument" in test_namespace

    def test_star_import_only_includes_all_list(self):
        """Verify star import doesn't include private or unlisted items."""
        # Create a clean namespace to test star import
        test_namespace = {}
        exec("from cli.utils import *", test_namespace)

        # Should not include private functions or imports
        assert "_build_feedback_prompt" not in test_namespace
        assert "_create_template_doc" not in test_namespace
        assert "_create_fallback_updates_doc" not in test_namespace


class TestPrivateFunctionsNotExported:
    """Test that private functions are not exported."""

    def test_private_functions_not_in_all(self):
        """Verify private helper functions are not in __all__."""
        from cli import utils

        private_functions = [
            "_build_feedback_prompt",
            "_create_template_doc",
            "_create_fallback_updates_doc",
        ]
        for func in private_functions:
            assert func not in utils.__all__

    def test_private_functions_not_accessible_via_star_import(self):
        """Verify private functions don't leak through star import."""
        test_namespace = {}
        exec("from cli.utils import *", test_namespace)

        assert "_build_feedback_prompt" not in test_namespace
        assert "_create_template_doc" not in test_namespace
        assert "_create_fallback_updates_doc" not in test_namespace


class TestImportsInRealModules:
    """Integration tests for imports in real modules."""

    def test_imports_work_in_temp_module(self, tmp_path):
        """Create temp Python file to verify imports from cli.utils work."""
        # Create a temp Python file
        test_file = tmp_path / "test_imports.py"
        test_file.write_text(
            """
from cli.utils import ReviewTargets, apply_review_feedback

# Try to instantiate ReviewTargets
def test_func():
    return ReviewTargets
"""
        )

        # Import the temp module
        import importlib.util

        spec = importlib.util.spec_from_file_location("test_imports", test_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Verify the imports worked
        assert hasattr(module, "test_func")
        result = module.test_func()
        assert result.__name__ == "ReviewTargets"


class TestBackwardsCompatibility:
    """Test backwards compatibility with existing code."""

    def test_existing_path_resolver_imports_still_work(self):
        """Verify imports from cli.utils.path_resolver still work."""
        from cli.utils.path_resolver import (
            PathResolutionError,
            resolve_file_argument,
        )

        # Verify these still work
        assert issubclass(PathResolutionError, Exception)
        assert callable(resolve_file_argument)

    def test_existing_review_feedback_imports_still_work(self):
        """Verify imports from cli.utils.review_feedback still work."""
        from cli.utils.review_feedback import (
            ReviewTargets,
            apply_review_feedback,
        )

        # Verify these still work
        assert hasattr(ReviewTargets, "__dataclass_fields__")
        assert callable(apply_review_feedback)

    def test_both_import_paths_refer_to_same_objects(self):
        """Verify importing from different paths returns the same objects."""
        from cli.utils import ReviewTargets as ReviewTargets1
        from cli.utils import apply_review_feedback as apply_review_feedback1
        from cli.utils.review_feedback import ReviewTargets as ReviewTargets2
        from cli.utils.review_feedback import (
            apply_review_feedback as apply_review_feedback2,
        )

        # Verify they're the same objects
        assert ReviewTargets1 is ReviewTargets2
        assert apply_review_feedback1 is apply_review_feedback2


class TestModuleStructure:
    """Test the overall module structure."""

    def test_module_has_docstring(self):
        """Verify cli.utils module has a docstring."""
        from cli import utils

        assert utils.__doc__ is not None
        assert len(utils.__doc__.strip()) > 0

    def test_module_imports_work_after_reload(self):
        """Verify imports still work after reloading the module."""
        from cli import utils

        # Reload the module
        importlib.reload(utils)

        # Verify imports still work
        from cli.utils import (
            PathResolutionError,
            ReviewTargets,
            apply_review_feedback,
            resolve_file_argument,
        )

        assert ReviewTargets is not None
        assert apply_review_feedback is not None
        assert PathResolutionError is not None
        assert resolve_file_argument is not None
