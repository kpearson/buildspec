"""Comprehensive unit tests for ValidationGate.

Tests all validation checks with passing and failing scenarios, including:
- Branch has commits check
- Final commit exists check
- Tests pass check
- Acceptance criteria check
- Various test_suite_status values
- Critical vs non-critical ticket behavior
- Empty acceptance criteria handling
"""

import pytest
from unittest.mock import Mock, patch

from cli.epic.gates import EpicContext
from cli.epic.git_operations import GitError, GitOperations
from cli.epic.models import AcceptanceCriterion, GateResult, GitInfo, Ticket, TicketState
from cli.epic.test_gates import ValidationGate


class TestValidationGateCheck:
    """Test the main check() method that runs all validation checks."""

    def test_all_checks_pass(self):
        """Test that check returns passed=True when all checks pass."""
        gate = ValidationGate()

        # Create ticket with all required fields
        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            critical=True,
            git_info=GitInfo(
                branch_name="ticket/test-ticket",
                base_commit="base123",
                final_commit="final456",
            ),
            test_suite_status="passing",
            acceptance_criteria=[
                AcceptanceCriterion(criterion="Criterion 1", met=True),
                AcceptanceCriterion(criterion="Criterion 2", met=True),
            ],
        )

        # Mock git operations
        mock_git = Mock(spec=GitOperations)
        mock_git.get_commits_between.return_value = ["commit1", "commit2"]
        mock_git.commit_exists.return_value = True
        mock_git.commit_on_branch.return_value = True

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={"test-ticket": ticket},
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket, context)

        assert result.passed is True
        assert result.reason == "All validation checks passed"

    def test_fails_on_first_failing_check(self):
        """Test that check returns first failure and stops processing."""
        gate = ValidationGate()

        # Create ticket with no commits on branch
        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            critical=True,
            git_info=GitInfo(
                branch_name="ticket/test-ticket",
                base_commit="base123",
                final_commit="final456",
            ),
            test_suite_status="passing",
            acceptance_criteria=[
                AcceptanceCriterion(criterion="Criterion 1", met=False),  # Unmet
            ],
        )

        # Mock git operations - no commits
        mock_git = Mock(spec=GitOperations)
        mock_git.get_commits_between.return_value = []  # No commits - will fail first

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={"test-ticket": ticket},
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket, context)

        assert result.passed is False
        assert result.reason == "No commits on ticket branch"
        # Should stop after first failure, not check acceptance criteria
        mock_git.commit_exists.assert_not_called()


class TestCheckBranchHasCommits:
    """Test _check_branch_has_commits validation."""

    def test_success_with_commits(self):
        """Test that check passes when branch has commits."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            git_info=GitInfo(
                branch_name="ticket/test-ticket",
                base_commit="base123",
            ),
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.get_commits_between.return_value = ["commit1", "commit2", "commit3"]

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=mock_git,
            epic_config={},
        )

        result = gate._check_branch_has_commits(ticket, context)

        assert result.passed is True
        assert result.metadata["commit_count"] == 3
        mock_git.get_commits_between.assert_called_once_with("base123", "ticket/test-ticket")

    def test_failure_with_no_commits(self):
        """Test that check fails when branch has no commits."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            git_info=GitInfo(
                branch_name="ticket/test-ticket",
                base_commit="base123",
            ),
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.get_commits_between.return_value = []

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=mock_git,
            epic_config={},
        )

        result = gate._check_branch_has_commits(ticket, context)

        assert result.passed is False
        assert result.reason == "No commits on ticket branch"

    def test_failure_with_missing_git_info(self):
        """Test that check fails when git_info is missing."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            git_info=None,
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=Mock(spec=GitOperations),
            epic_config={},
        )

        result = gate._check_branch_has_commits(ticket, context)

        assert result.passed is False
        assert result.reason == "Missing git info"

    def test_failure_with_missing_branch_name(self):
        """Test that check fails when branch_name is missing."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            git_info=GitInfo(branch_name=None, base_commit="base123"),
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=Mock(spec=GitOperations),
            epic_config={},
        )

        result = gate._check_branch_has_commits(ticket, context)

        assert result.passed is False
        assert result.reason == "Missing git info"

    def test_failure_on_git_error(self):
        """Test that check fails gracefully on GitError."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            git_info=GitInfo(
                branch_name="ticket/test-ticket",
                base_commit="base123",
            ),
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.get_commits_between.side_effect = GitError("Branch not found")

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=mock_git,
            epic_config={},
        )

        result = gate._check_branch_has_commits(ticket, context)

        assert result.passed is False
        assert "Git error" in result.reason
        assert "Branch not found" in result.reason

    def test_success_with_single_commit(self):
        """Test that check passes with exactly one commit."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            git_info=GitInfo(
                branch_name="ticket/test-ticket",
                base_commit="base123",
            ),
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.get_commits_between.return_value = ["commit1"]

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=mock_git,
            epic_config={},
        )

        result = gate._check_branch_has_commits(ticket, context)

        assert result.passed is True
        assert result.metadata["commit_count"] == 1


class TestCheckFinalCommitExists:
    """Test _check_final_commit_exists validation."""

    def test_success_when_commit_exists_and_on_branch(self):
        """Test that check passes when final commit exists and is on branch."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            git_info=GitInfo(
                branch_name="ticket/test-ticket",
                final_commit="final123",
            ),
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.commit_exists.return_value = True
        mock_git.commit_on_branch.return_value = True

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=mock_git,
            epic_config={},
        )

        result = gate._check_final_commit_exists(ticket, context)

        assert result.passed is True
        mock_git.commit_exists.assert_called_once_with("final123")
        mock_git.commit_on_branch.assert_called_once_with("final123", "ticket/test-ticket")

    def test_failure_when_commit_does_not_exist(self):
        """Test that check fails when final commit does not exist."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            git_info=GitInfo(
                branch_name="ticket/test-ticket",
                final_commit="final123",
            ),
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.commit_exists.return_value = False

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=mock_git,
            epic_config={},
        )

        result = gate._check_final_commit_exists(ticket, context)

        assert result.passed is False
        assert "Final commit does not exist" in result.reason
        assert "final123" in result.reason
        # Should not check if on branch since commit doesn't exist
        mock_git.commit_on_branch.assert_not_called()

    def test_failure_when_commit_not_on_branch(self):
        """Test that check fails when final commit is not on branch."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            git_info=GitInfo(
                branch_name="ticket/test-ticket",
                final_commit="final123",
            ),
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.commit_exists.return_value = True
        mock_git.commit_on_branch.return_value = False

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=mock_git,
            epic_config={},
        )

        result = gate._check_final_commit_exists(ticket, context)

        assert result.passed is False
        assert "Final commit not on branch" in result.reason
        assert "final123" in result.reason

    def test_failure_with_missing_git_info(self):
        """Test that check fails when git_info is missing."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            git_info=None,
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=Mock(spec=GitOperations),
            epic_config={},
        )

        result = gate._check_final_commit_exists(ticket, context)

        assert result.passed is False
        assert result.reason == "Missing final_commit"

    def test_failure_with_missing_final_commit(self):
        """Test that check fails when final_commit is missing."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            git_info=GitInfo(
                branch_name="ticket/test-ticket",
                final_commit=None,
            ),
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=Mock(spec=GitOperations),
            epic_config={},
        )

        result = gate._check_final_commit_exists(ticket, context)

        assert result.passed is False
        assert result.reason == "Missing final_commit"


class TestCheckTestsPass:
    """Test _check_tests_pass validation."""

    def test_success_with_passing_tests(self):
        """Test that check passes when test_suite_status is 'passing'."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            test_suite_status="passing",
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=Mock(spec=GitOperations),
            epic_config={},
        )

        result = gate._check_tests_pass(ticket, context)

        assert result.passed is True

    def test_success_with_skipped_tests_non_critical(self):
        """Test that check passes when tests skipped for non-critical ticket."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            critical=False,
            test_suite_status="skipped",
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=Mock(spec=GitOperations),
            epic_config={},
        )

        result = gate._check_tests_pass(ticket, context)

        assert result.passed is True
        assert result.metadata["skipped"] is True

    def test_failure_with_skipped_tests_critical(self):
        """Test that check fails when tests skipped for critical ticket."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            critical=True,
            test_suite_status="skipped",
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=Mock(spec=GitOperations),
            epic_config={},
        )

        result = gate._check_tests_pass(ticket, context)

        assert result.passed is False
        assert "Tests not passing" in result.reason
        assert "skipped" in result.reason

    def test_failure_with_failing_tests(self):
        """Test that check fails when test_suite_status is 'failing'."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            test_suite_status="failing",
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=Mock(spec=GitOperations),
            epic_config={},
        )

        result = gate._check_tests_pass(ticket, context)

        assert result.passed is False
        assert "Tests not passing" in result.reason
        assert "failing" in result.reason

    def test_failure_with_error_status(self):
        """Test that check fails when test_suite_status is 'error'."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            test_suite_status="error",
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=Mock(spec=GitOperations),
            epic_config={},
        )

        result = gate._check_tests_pass(ticket, context)

        assert result.passed is False
        assert "Tests not passing" in result.reason
        assert "error" in result.reason

    def test_failure_with_none_status(self):
        """Test that check fails when test_suite_status is None."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            test_suite_status=None,
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=Mock(spec=GitOperations),
            epic_config={},
        )

        result = gate._check_tests_pass(ticket, context)

        assert result.passed is False
        assert "Tests not passing" in result.reason

    def test_critical_ticket_requires_passing_tests(self):
        """Test that critical tickets must have passing tests, not skipped."""
        gate = ValidationGate()

        # Critical ticket with skipped tests should fail
        critical_ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            critical=True,
            test_suite_status="skipped",
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=Mock(spec=GitOperations),
            epic_config={},
        )

        result = gate._check_tests_pass(critical_ticket, context)
        assert result.passed is False

        # Same ticket but passing should succeed
        critical_ticket.test_suite_status = "passing"
        result = gate._check_tests_pass(critical_ticket, context)
        assert result.passed is True


class TestCheckAcceptanceCriteria:
    """Test _check_acceptance_criteria validation."""

    def test_success_with_all_criteria_met(self):
        """Test that check passes when all acceptance criteria are met."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            acceptance_criteria=[
                AcceptanceCriterion(criterion="Criterion 1", met=True),
                AcceptanceCriterion(criterion="Criterion 2", met=True),
                AcceptanceCriterion(criterion="Criterion 3", met=True),
            ],
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=Mock(spec=GitOperations),
            epic_config={},
        )

        result = gate._check_acceptance_criteria(ticket, context)

        assert result.passed is True

    def test_success_with_empty_criteria_list(self):
        """Test that check passes when acceptance criteria list is empty."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            acceptance_criteria=[],
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=Mock(spec=GitOperations),
            epic_config={},
        )

        result = gate._check_acceptance_criteria(ticket, context)

        assert result.passed is True
        assert result.reason == "No acceptance criteria"

    def test_success_with_none_criteria(self):
        """Test that check passes when acceptance criteria is None."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            acceptance_criteria=None,
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=Mock(spec=GitOperations),
            epic_config={},
        )

        result = gate._check_acceptance_criteria(ticket, context)

        assert result.passed is True
        assert result.reason == "No acceptance criteria"

    def test_failure_with_one_unmet_criterion(self):
        """Test that check fails when one criterion is not met."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            acceptance_criteria=[
                AcceptanceCriterion(criterion="Criterion 1", met=True),
                AcceptanceCriterion(criterion="Criterion 2", met=False),
                AcceptanceCriterion(criterion="Criterion 3", met=True),
            ],
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=Mock(spec=GitOperations),
            epic_config={},
        )

        result = gate._check_acceptance_criteria(ticket, context)

        assert result.passed is False
        assert "Unmet acceptance criteria" in result.reason
        assert "Criterion 2" in result.reason

    def test_failure_with_multiple_unmet_criteria(self):
        """Test that check fails and lists all unmet criteria."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            acceptance_criteria=[
                AcceptanceCriterion(criterion="Criterion 1", met=False),
                AcceptanceCriterion(criterion="Criterion 2", met=True),
                AcceptanceCriterion(criterion="Criterion 3", met=False),
                AcceptanceCriterion(criterion="Criterion 4", met=False),
            ],
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=Mock(spec=GitOperations),
            epic_config={},
        )

        result = gate._check_acceptance_criteria(ticket, context)

        assert result.passed is False
        assert "Unmet acceptance criteria" in result.reason
        assert "Criterion 1" in result.reason
        assert "Criterion 3" in result.reason
        assert "Criterion 4" in result.reason
        # Met criterion should not be in failure reason
        assert "Criterion 2" not in result.reason

    def test_failure_with_all_unmet_criteria(self):
        """Test that check fails when all criteria are unmet."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            acceptance_criteria=[
                AcceptanceCriterion(criterion="Criterion 1", met=False),
                AcceptanceCriterion(criterion="Criterion 2", met=False),
            ],
        )

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=Mock(spec=GitOperations),
            epic_config={},
        )

        result = gate._check_acceptance_criteria(ticket, context)

        assert result.passed is False
        assert "Unmet acceptance criteria" in result.reason
        assert "Criterion 1" in result.reason
        assert "Criterion 2" in result.reason


class TestValidationGateIntegration:
    """Integration tests for ValidationGate with multiple scenarios."""

    def test_complete_validation_success_scenario(self):
        """Test complete validation with all checks passing."""
        gate = ValidationGate()

        ticket = Ticket(
            id="feature-ticket",
            path="/path/feature",
            title="Implement Feature X",
            critical=True,
            state=TicketState.AWAITING_VALIDATION,
            git_info=GitInfo(
                branch_name="ticket/feature-ticket",
                base_commit="abc123",
                final_commit="xyz789",
            ),
            test_suite_status="passing",
            acceptance_criteria=[
                AcceptanceCriterion(criterion="Feature implemented", met=True),
                AcceptanceCriterion(criterion="Tests added", met=True),
                AcceptanceCriterion(criterion="Documentation updated", met=True),
            ],
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.get_commits_between.return_value = ["commit1", "commit2", "commit3"]
        mock_git.commit_exists.return_value = True
        mock_git.commit_on_branch.return_value = True

        context = EpicContext(
            epic_id="feature-epic",
            epic_branch="epic/feature",
            baseline_commit="baseline123",
            tickets={"feature-ticket": ticket},
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket, context)

        assert result.passed is True
        assert result.reason == "All validation checks passed"

        # Verify all git operations were called
        mock_git.get_commits_between.assert_called_once()
        mock_git.commit_exists.assert_called_once()
        mock_git.commit_on_branch.assert_called_once()

    def test_non_critical_ticket_with_skipped_tests(self):
        """Test that non-critical tickets can skip tests."""
        gate = ValidationGate()

        ticket = Ticket(
            id="docs-ticket",
            path="/path/docs",
            title="Update Documentation",
            critical=False,
            git_info=GitInfo(
                branch_name="ticket/docs-ticket",
                base_commit="abc123",
                final_commit="xyz789",
            ),
            test_suite_status="skipped",
            acceptance_criteria=[
                AcceptanceCriterion(criterion="Docs updated", met=True),
            ],
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.get_commits_between.return_value = ["commit1"]
        mock_git.commit_exists.return_value = True
        mock_git.commit_on_branch.return_value = True

        context = EpicContext(
            epic_id="docs-epic",
            epic_branch="epic/docs",
            baseline_commit="baseline123",
            tickets={"docs-ticket": ticket},
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket, context)

        assert result.passed is True

    def test_critical_ticket_cannot_skip_tests(self):
        """Test that critical tickets must have passing tests."""
        gate = ValidationGate()

        ticket = Ticket(
            id="critical-ticket",
            path="/path/critical",
            title="Critical Security Fix",
            critical=True,
            git_info=GitInfo(
                branch_name="ticket/critical-ticket",
                base_commit="abc123",
                final_commit="xyz789",
            ),
            test_suite_status="skipped",
            acceptance_criteria=[
                AcceptanceCriterion(criterion="Security fix applied", met=True),
            ],
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.get_commits_between.return_value = ["commit1"]
        mock_git.commit_exists.return_value = True
        mock_git.commit_on_branch.return_value = True

        context = EpicContext(
            epic_id="security-epic",
            epic_branch="epic/security",
            baseline_commit="baseline123",
            tickets={"critical-ticket": ticket},
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket, context)

        assert result.passed is False
        assert "Tests not passing" in result.reason

    def test_ticket_with_no_acceptance_criteria(self):
        """Test validation passes with no acceptance criteria."""
        gate = ValidationGate()

        ticket = Ticket(
            id="simple-ticket",
            path="/path/simple",
            title="Simple Change",
            critical=False,
            git_info=GitInfo(
                branch_name="ticket/simple-ticket",
                base_commit="abc123",
                final_commit="xyz789",
            ),
            test_suite_status="passing",
            acceptance_criteria=[],  # Empty list
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.get_commits_between.return_value = ["commit1"]
        mock_git.commit_exists.return_value = True
        mock_git.commit_on_branch.return_value = True

        context = EpicContext(
            epic_id="simple-epic",
            epic_branch="epic/simple",
            baseline_commit="baseline123",
            tickets={"simple-ticket": ticket},
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket, context)

        assert result.passed is True

    def test_validation_stops_at_first_failure(self):
        """Test that validation stops at first failing check."""
        gate = ValidationGate()

        ticket = Ticket(
            id="bad-ticket",
            path="/path/bad",
            title="Bad Ticket",
            critical=True,
            git_info=GitInfo(
                branch_name="ticket/bad-ticket",
                base_commit="abc123",
                final_commit="xyz789",
            ),
            test_suite_status="failing",  # Will fail at test check
            acceptance_criteria=[
                AcceptanceCriterion(criterion="Criterion", met=False),  # Also unmet
            ],
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.get_commits_between.return_value = ["commit1"]
        mock_git.commit_exists.return_value = True
        mock_git.commit_on_branch.return_value = True

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={"bad-ticket": ticket},
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket, context)

        assert result.passed is False
        # Should fail at test check, not acceptance criteria
        assert "Tests not passing" in result.reason
        assert "failing" in result.reason

    def test_git_error_during_validation(self):
        """Test that git errors are handled gracefully."""
        gate = ValidationGate()

        ticket = Ticket(
            id="test-ticket",
            path="/path/test",
            title="Test Ticket",
            critical=True,
            git_info=GitInfo(
                branch_name="ticket/test-ticket",
                base_commit="abc123",
                final_commit="xyz789",
            ),
            test_suite_status="passing",
            acceptance_criteria=[],
        )

        mock_git = Mock(spec=GitOperations)
        mock_git.get_commits_between.side_effect = GitError("Repository not found")

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={"test-ticket": ticket},
            git=mock_git,
            epic_config={},
        )

        result = gate.check(ticket, context)

        assert result.passed is False
        assert "Git error" in result.reason
        assert "Repository not found" in result.reason

    def test_various_test_status_values(self):
        """Test validation with different test_suite_status values."""
        gate = ValidationGate()

        mock_git = Mock(spec=GitOperations)
        mock_git.get_commits_between.return_value = ["commit1"]
        mock_git.commit_exists.return_value = True
        mock_git.commit_on_branch.return_value = True

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test",
            baseline_commit="baseline123",
            tickets={},
            git=mock_git,
            epic_config={},
        )

        # Test passing status
        ticket = Ticket(
            id="test-1",
            path="/path/1",
            title="Test 1",
            git_info=GitInfo(branch_name="ticket/test-1", base_commit="abc", final_commit="xyz"),
            test_suite_status="passing",
        )
        result = gate.check(ticket, context)
        assert result.passed is True

        # Test failing status
        ticket.test_suite_status = "failing"
        result = gate.check(ticket, context)
        assert result.passed is False

        # Test error status
        ticket.test_suite_status = "error"
        result = gate.check(ticket, context)
        assert result.passed is False

        # Test skipped on non-critical
        ticket.test_suite_status = "skipped"
        ticket.critical = False
        result = gate.check(ticket, context)
        assert result.passed is True

        # Test skipped on critical
        ticket.critical = True
        result = gate.check(ticket, context)
        assert result.passed is False
