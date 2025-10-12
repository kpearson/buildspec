"""Unit tests for gate protocol and context."""

import pytest
from cli.epic.gates import EpicContext, TransitionGate
from cli.epic.git_operations import GitOperations
from cli.epic.models import GateResult, Ticket, TicketState


class TestEpicContext:
    """Test EpicContext dataclass."""

    def test_minimal_initialization(self):
        """Test initialization with minimal required fields."""
        git_ops = GitOperations()
        tickets = {}
        epic_config = {}

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test-epic",
            baseline_commit="abc123",
            tickets=tickets,
            git=git_ops,
            epic_config=epic_config,
        )

        assert context.epic_id == "test-epic"
        assert context.epic_branch == "epic/test-epic"
        assert context.baseline_commit == "abc123"
        assert context.tickets == {}
        assert context.git == git_ops
        assert context.epic_config == {}

    def test_full_initialization(self):
        """Test initialization with full context."""
        git_ops = GitOperations(repo_path="/tmp/test-repo")
        tickets = {
            "ticket-1": Ticket(id="ticket-1", path="/path/1", title="Ticket 1"),
            "ticket-2": Ticket(
                id="ticket-2",
                path="/path/2",
                title="Ticket 2",
                depends_on=["ticket-1"],
            ),
        }
        epic_config = {
            "rollback_on_failure": True,
            "ticket_count": 2,
        }

        context = EpicContext(
            epic_id="complex-epic",
            epic_branch="epic/complex-epic",
            baseline_commit="def456",
            tickets=tickets,
            git=git_ops,
            epic_config=epic_config,
        )

        assert context.epic_id == "complex-epic"
        assert context.epic_branch == "epic/complex-epic"
        assert context.baseline_commit == "def456"
        assert len(context.tickets) == 2
        assert "ticket-1" in context.tickets
        assert "ticket-2" in context.tickets
        assert context.tickets["ticket-2"].depends_on == ["ticket-1"]
        assert context.git.repo_path == "/tmp/test-repo"
        assert context.epic_config["rollback_on_failure"] is True
        assert context.epic_config["ticket_count"] == 2

    def test_ticket_dictionary_access(self):
        """Test accessing tickets via dictionary."""
        ticket1 = Ticket(id="ticket-1", path="/path/1", title="Ticket 1")
        ticket2 = Ticket(
            id="ticket-2",
            path="/path/2",
            title="Ticket 2",
            state=TicketState.COMPLETED,
        )
        tickets = {"ticket-1": ticket1, "ticket-2": ticket2}

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test-epic",
            baseline_commit="abc123",
            tickets=tickets,
            git=GitOperations(),
            epic_config={},
        )

        # Test dictionary operations
        assert context.tickets["ticket-1"] == ticket1
        assert context.tickets["ticket-2"] == ticket2
        assert context.tickets["ticket-2"].state == TicketState.COMPLETED
        assert len(context.tickets) == 2
        assert "ticket-1" in context.tickets
        assert "ticket-3" not in context.tickets

    def test_epic_config_access(self):
        """Test accessing various epic config fields."""
        epic_config = {
            "rollback_on_failure": False,
            "ticket_count": 5,
            "acceptance_criteria": ["Criteria 1", "Criteria 2"],
            "coordination_requirements": {
                "function_profiles": {},
            },
        }

        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test-epic",
            baseline_commit="abc123",
            tickets={},
            git=GitOperations(),
            epic_config=epic_config,
        )

        assert context.epic_config["rollback_on_failure"] is False
        assert context.epic_config["ticket_count"] == 5
        assert len(context.epic_config["acceptance_criteria"]) == 2
        assert "coordination_requirements" in context.epic_config

    def test_mutable_tickets_dict(self):
        """Test that tickets dictionary is mutable."""
        context = EpicContext(
            epic_id="test-epic",
            epic_branch="epic/test-epic",
            baseline_commit="abc123",
            tickets={},
            git=GitOperations(),
            epic_config={},
        )

        # Should be able to add tickets
        new_ticket = Ticket(id="new-ticket", path="/path/new", title="New Ticket")
        context.tickets["new-ticket"] = new_ticket
        assert "new-ticket" in context.tickets
        assert context.tickets["new-ticket"] == new_ticket


class TestTransitionGateProtocol:
    """Test TransitionGate protocol definition and usage."""

    def test_mock_gate_implementation(self):
        """Test that a mock gate correctly implements the protocol."""

        class MockPassingGate:
            """Mock gate that always passes."""

            def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
                return GateResult(passed=True, metadata={"gate": "mock"})

        gate = MockPassingGate()
        ticket = Ticket(id="test-ticket", path="/path", title="Test")
        context = EpicContext(
            epic_id="epic",
            epic_branch="epic/test",
            baseline_commit="abc",
            tickets={},
            git=GitOperations(),
            epic_config={},
        )

        result = gate.check(ticket, context)
        assert result.passed is True
        assert result.metadata["gate"] == "mock"

    def test_mock_gate_implementation_with_failure(self):
        """Test that a mock gate can return failure."""

        class MockFailingGate:
            """Mock gate that always fails."""

            def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
                return GateResult(
                    passed=False,
                    reason="Mock validation failed",
                )

        gate = MockFailingGate()
        ticket = Ticket(id="test-ticket", path="/path", title="Test")
        context = EpicContext(
            epic_id="epic",
            epic_branch="epic/test",
            baseline_commit="abc",
            tickets={},
            git=GitOperations(),
            epic_config={},
        )

        result = gate.check(ticket, context)
        assert result.passed is False
        assert result.reason == "Mock validation failed"

    def test_mock_gate_with_context_access(self):
        """Test that gate can access context fields."""

        class MockContextGate:
            """Mock gate that uses context."""

            def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
                # Gate can access all context fields
                epic_id = context.epic_id
                baseline = context.baseline_commit
                ticket_count = len(context.tickets)

                return GateResult(
                    passed=True,
                    metadata={
                        "epic_id": epic_id,
                        "baseline": baseline,
                        "ticket_count": ticket_count,
                    },
                )

        gate = MockContextGate()
        ticket = Ticket(id="test-ticket", path="/path", title="Test")
        tickets = {
            "ticket-1": Ticket(id="ticket-1", path="/path/1", title="Ticket 1"),
            "ticket-2": Ticket(id="ticket-2", path="/path/2", title="Ticket 2"),
        }
        context = EpicContext(
            epic_id="my-epic",
            epic_branch="epic/my-epic",
            baseline_commit="baseline123",
            tickets=tickets,
            git=GitOperations(),
            epic_config={},
        )

        result = gate.check(ticket, context)
        assert result.passed is True
        assert result.metadata["epic_id"] == "my-epic"
        assert result.metadata["baseline"] == "baseline123"
        assert result.metadata["ticket_count"] == 2

    def test_mock_gate_with_ticket_validation(self):
        """Test that gate can validate ticket fields."""

        class MockTicketValidationGate:
            """Mock gate that validates ticket fields."""

            def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
                # Check if ticket is critical
                if not ticket.critical:
                    return GateResult(
                        passed=False,
                        reason="Only critical tickets allowed",
                    )

                # Check if ticket has dependencies
                if ticket.depends_on:
                    return GateResult(
                        passed=False,
                        reason="Tickets with dependencies not allowed",
                    )

                return GateResult(passed=True)

        gate = MockTicketValidationGate()

        # Test with non-critical ticket
        non_critical_ticket = Ticket(
            id="test-1",
            path="/path",
            title="Test",
            critical=False,
        )
        context = EpicContext(
            epic_id="epic",
            epic_branch="epic/test",
            baseline_commit="abc",
            tickets={},
            git=GitOperations(),
            epic_config={},
        )
        result = gate.check(non_critical_ticket, context)
        assert result.passed is False
        assert "critical" in result.reason

        # Test with ticket that has dependencies
        dependent_ticket = Ticket(
            id="test-2",
            path="/path",
            title="Test",
            critical=True,
            depends_on=["test-1"],
        )
        result = gate.check(dependent_ticket, context)
        assert result.passed is False
        assert "dependencies" in result.reason

        # Test with valid ticket
        valid_ticket = Ticket(
            id="test-3",
            path="/path",
            title="Test",
            critical=True,
        )
        result = gate.check(valid_ticket, context)
        assert result.passed is True

    def test_mock_gate_with_dependency_checking(self):
        """Test that gate can check ticket dependencies via context."""

        class MockDependencyGate:
            """Mock gate that checks if dependencies are completed."""

            def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
                # Check all dependencies are completed
                for dep_id in ticket.depends_on:
                    if dep_id not in context.tickets:
                        return GateResult(
                            passed=False,
                            reason=f"Dependency {dep_id} not found",
                        )

                    dep_ticket = context.tickets[dep_id]
                    if dep_ticket.state != TicketState.COMPLETED:
                        return GateResult(
                            passed=False,
                            reason=f"Dependency {dep_id} not completed (state: {dep_ticket.state})",
                        )

                return GateResult(passed=True)

        gate = MockDependencyGate()

        # Create context with tickets in different states
        ticket1 = Ticket(
            id="ticket-1",
            path="/path/1",
            title="Ticket 1",
            state=TicketState.COMPLETED,
        )
        ticket2 = Ticket(
            id="ticket-2",
            path="/path/2",
            title="Ticket 2",
            state=TicketState.IN_PROGRESS,
        )
        tickets = {"ticket-1": ticket1, "ticket-2": ticket2}
        context = EpicContext(
            epic_id="epic",
            epic_branch="epic/test",
            baseline_commit="abc",
            tickets=tickets,
            git=GitOperations(),
            epic_config={},
        )

        # Test with completed dependency (should pass)
        ticket_with_completed_dep = Ticket(
            id="ticket-3",
            path="/path/3",
            title="Ticket 3",
            depends_on=["ticket-1"],
        )
        result = gate.check(ticket_with_completed_dep, context)
        assert result.passed is True

        # Test with in-progress dependency (should fail)
        ticket_with_incomplete_dep = Ticket(
            id="ticket-4",
            path="/path/4",
            title="Ticket 4",
            depends_on=["ticket-2"],
        )
        result = gate.check(ticket_with_incomplete_dep, context)
        assert result.passed is False
        assert "ticket-2" in result.reason
        assert "not completed" in result.reason

        # Test with missing dependency (should fail)
        ticket_with_missing_dep = Ticket(
            id="ticket-5",
            path="/path/5",
            title="Ticket 5",
            depends_on=["ticket-99"],
        )
        result = gate.check(ticket_with_missing_dep, context)
        assert result.passed is False
        assert "ticket-99" in result.reason
        assert "not found" in result.reason

    def test_mock_gate_is_callable(self):
        """Test that gate instances are callable via check method."""

        class MockGate:
            def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
                return GateResult(passed=True)

        gate = MockGate()
        ticket = Ticket(id="test", path="/path", title="Test")
        context = EpicContext(
            epic_id="epic",
            epic_branch="epic/test",
            baseline_commit="abc",
            tickets={},
            git=GitOperations(),
            epic_config={},
        )

        # Should be able to call check method
        result = gate.check(ticket, context)
        assert isinstance(result, GateResult)
        assert result.passed is True

    def test_protocol_type_checking_with_typing(self):
        """Test that protocol works with type checking (runtime check)."""
        from typing import get_type_hints

        # Verify TransitionGate is a Protocol
        assert hasattr(TransitionGate, "__mro__")

        # Verify it has the expected method
        hints = get_type_hints(TransitionGate.check)
        assert "ticket" in hints
        assert "context" in hints
        assert "return" in hints

    def test_multiple_gate_implementations(self):
        """Test that multiple gates can coexist with different logic."""

        class AlwaysPassGate:
            def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
                return GateResult(passed=True, reason="Always passes")

        class AlwaysFailGate:
            def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
                return GateResult(passed=False, reason="Always fails")

        class ConditionalGate:
            def check(self, ticket: Ticket, context: EpicContext) -> GateResult:
                if ticket.critical:
                    return GateResult(passed=True)
                return GateResult(passed=False, reason="Not critical")

        ticket = Ticket(id="test", path="/path", title="Test", critical=True)
        context = EpicContext(
            epic_id="epic",
            epic_branch="epic/test",
            baseline_commit="abc",
            tickets={},
            git=GitOperations(),
            epic_config={},
        )

        # Test all gates
        always_pass = AlwaysPassGate()
        always_fail = AlwaysFailGate()
        conditional = ConditionalGate()

        assert always_pass.check(ticket, context).passed is True
        assert always_fail.check(ticket, context).passed is False
        assert conditional.check(ticket, context).passed is True

        # Change ticket to non-critical
        ticket.critical = False
        assert conditional.check(ticket, context).passed is False
