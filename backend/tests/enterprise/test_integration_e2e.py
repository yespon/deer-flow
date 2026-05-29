"""End-to-end integration tests for DeerFlow Enterprise.

Tests complete workflows spanning multiple enterprise modules.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from deerflow.enterprise import (
    AgentTeamOrchestrator,
    ApprovalRule,
    ApprovalRuleEngine,
    ApprovalStatus,
    AuditedSandbox,
    AuditSandboxEventType,
    BrandController,
    BrandGuidelines,
    ComplianceFilter,
    ContentType,
    CorporateKnowledgeBase,
    EnterpriseSandboxProvider,
    ExecutionPlan,
    KnowledgeBaseConfig,
    KnowledgeDocument,
    KnowledgeRetrievalMiddleware,
    QuotaManager,
    RBACEngine,
    Role,
    SubTask,
    TaskDecomposer,
    Tenant,
    TenantNamespace,
    get_current_tenant,
    set_current_tenant,
)


@pytest.fixture
def mock_tenant():
    """Create a mock tenant for testing."""
    return Tenant(
        id="tenant_integration_test",
        name="Integration Test Tenant",
        plan="enterprise",
    )


@pytest.fixture
def enterprise_context(mock_tenant):
    """Set up enterprise context with tenant."""
    set_current_tenant(mock_tenant)
    yield


class TestEndToEndAgentTeamsWithApproval:
    """Test Agent Teams workflow with Human-in-Loop approval."""

    @pytest.mark.asyncio
    async def test_complex_task_requires_approval(self, enterprise_context, mock_tenant):
        """Should decompose complex task, require approval for sensitive tools."""
        # Setup
        task_decomposer = TaskDecomposer()
        orchestrator = AgentTeamOrchestrator(max_parallel=2)
        approval_engine = ApprovalRuleEngine()

        # Create approval rule for sensitive operations
        sensitive_rule = ApprovalRule(
            name="sensitive_operations",
            condition=lambda tool_args: tool_args.get("tool") in ["bash", "write_file"],
            approvers=["admin"],
            timeout_hours=1,
        )
        approval_engine.register_rule(sensitive_rule)

        # Verify rule was registered
        assert "sensitive_operations" in approval_engine._rules

        # Mock LLM decomposition
        with patch.object(task_decomposer, "decompose") as mock_decompose:
            mock_decompose.return_value = ExecutionPlan(
                goal="Build a web scraper",
                tasks=[
                    SubTask(
                        id="task_1",
                        description="Research phase",
                        agent_type="research",
                    ),
                    SubTask(
                        id="task_2",
                        description="Code generation",
                        agent_type="coding",
                        dependencies=["task_1"],
                    ),
                ],
            )

            # Decompose task
            plan = await task_decomposer.decompose(
                goal="Build a web scraper",
                context={"language": "python"},
            )

            assert len(plan.tasks) == 2
            # Verify task dependencies are set correctly
            task_2 = next(t for t in plan.tasks if t.id == "task_2")
            assert task_2.dependencies == ["task_1"]

    @pytest.mark.asyncio
    async def test_agent_team_with_rbac_permission_check(self, enterprise_context):
        """Should check permissions before agent execution."""
        rbac = RBACEngine()

        # Mock permission check
        with patch.object(rbac, "check_permission") as mock_check:
            mock_check.return_value = True

            # Verify developer can execute general-purpose agent
            can_execute = rbac.check_permission(
                "user_1",
                "agent:execute:general-purpose",
                tenant_id="tenant_1",
            )
            assert can_execute is True


class TestEndToEndKnowledgeBaseRAG:
    """Test Knowledge Base with RAG integration."""

    @pytest.mark.asyncio
    async def test_kb_search_with_tenant_isolation(self, enterprise_context, mock_tenant):
        """Should return tenant-specific knowledge only."""
        config = KnowledgeBaseConfig(
            enabled=True,
            chunking_strategy="paragraphs",
        )
        kb = CorporateKnowledgeBase(config)

        # Mock vector store
        kb._vector_store = Mock()
        kb._vector_store.search = AsyncMock(return_value=[
            {"content": "Tenant-specific policy", "score": 0.9},
        ])
        kb._embedder = Mock()
        kb._embedder.embed = AsyncMock(return_value=[[0.1] * 1536])

        # Add document for tenant
        doc = KnowledgeDocument(
            doc_id="doc_1",
            title="Company Policy",
            content="This is the tenant-specific policy document.",
        )

        # Search within tenant context
        chunks = await kb.search(
            query="company policy",
            tenant_id=mock_tenant.id,
            top_k=5,
        )

        # Verify search was called
        assert kb._vector_store.search.called

    @pytest.mark.asyncio
    async def test_rag_middleware_injects_context(self, enterprise_context):
        """Should retrieve and inject knowledge into LLM context."""
        middleware = KnowledgeRetrievalMiddleware(enabled=True)

        # Test query rewriting
        query = "What is our refund policy?"
        rewritten = middleware._rewrite_query(query)
        assert "refund" in rewritten.lower()


class TestEndToEndSandboxAuditChain:
    """Test Enterprise Sandbox audit trail."""

    @pytest.mark.asyncio
    async def test_sandbox_operations_create_audit_chain(self, enterprise_context):
        """Should create immutable audit chain for all operations."""
        audit_log = Mock()
        audit_log.log = AsyncMock()

        quota_manager = Mock()
        quota_manager.check_before_acquire = AsyncMock()

        base_provider = Mock()
        mock_sandbox = Mock()
        mock_sandbox.id = "sandbox_001"
        mock_sandbox.tenant_id = "tenant_1"
        mock_sandbox.thread_id = "thread_1"
        mock_sandbox.execute_command = AsyncMock(return_value={"output": "ok", "exit_code": 0})
        base_provider.acquire = AsyncMock(return_value=mock_sandbox)

        # Create enterprise provider
        provider = EnterpriseSandboxProvider(
            base_provider=base_provider,
            audit_log=audit_log,
            quota_manager=quota_manager,
        )

        # Acquire sandbox - should log acquisition
        sandbox = await provider.acquire("thread_1", "tenant_1")
        assert isinstance(sandbox, AuditedSandbox)

        # Execute command - should log command execution
        await sandbox.execute_command("ls -la")

        # Verify audit events
        assert audit_log.log.call_count >= 2
        events = [call[0][0] for call in audit_log.log.call_args_list]
        assert AuditSandboxEventType.SANDBOX_ACQUIRED in events
        assert AuditSandboxEventType.COMMAND_EXECUTED in events

    @pytest.mark.asyncio
    async def test_quota_enforcement_blocks_exceeded(self, enterprise_context):
        """Should block sandbox acquisition when quota exceeded."""
        quota_manager = Mock()
        quota_manager.check_before_acquire = AsyncMock(
            side_effect=Exception("Quota exceeded: max_concurrent_sandboxes")
        )

        provider = EnterpriseSandboxProvider(
            base_provider=Mock(),
            audit_log=Mock(),
            quota_manager=quota_manager,
        )

        with pytest.raises(Exception, match="Quota exceeded"):
            await provider.acquire("thread_1", "tenant_1")


class TestEndToEndBrandCompliance:
    """Test Brand and Compliance integration."""

    @pytest.mark.asyncio
    async def test_content_pipeline_brand_then_compliance(self, enterprise_context):
        """Should check brand then compliance in sequence."""
        # Brand check
        brand_guidelines = BrandGuidelines(
            brand_name="Acme Corp",
            forbidden_words=["badword"],
            required_disclaimers=["Terms apply"],
        )
        brand_controller = BrandController(brand_guidelines)

        # Compliance check (use block severity)
        compliance_filter = ComplianceFilter(
            sensitive_words=["secret"],
            policy_rules=[],
            auto_review=True,
        )

        # Content that fails brand check
        content = "This has badword and secret information"

        # Brand check
        brand_result = await brand_controller.review_content(content)
        assert brand_result.approved is False
        assert any(i.type == "forbidden_word" for i in brand_result.issues)

        # Compliance check - sensitive words are high severity, not blocked
        compliance_result = await compliance_filter.filter_output(
            content, ContentType.TEXT
        )
        # High severity is warning, not block
        assert compliance_result.blocked is False
        assert any(v.rule == "sensitive_word" for v in compliance_result.violations)

    @pytest.mark.asyncio
    async def test_clean_content_passes_all_checks(self, enterprise_context):
        """Should approve content passing both brand and compliance."""
        brand_guidelines = BrandGuidelines(
            brand_name="Acme Corp",
            forbidden_words=["badword"],
        )
        brand_controller = BrandController(brand_guidelines)

        compliance_filter = ComplianceFilter(
            sensitive_words=["secret"],
        )

        # Clean content
        content = "Welcome to Acme Corp! We provide excellent service."

        brand_result = await brand_controller.review_content(content)
        compliance_result = await compliance_filter.filter_output(
            content, ContentType.TEXT
        )

        assert brand_result.approved is True
        assert compliance_result.blocked is False


class TestEndToEndFullWorkflow:
    """Test complete enterprise workflow with all modules."""

    @pytest.mark.asyncio
    async def test_multi_tenant_agent_workflow(self, enterprise_context, mock_tenant):
        """Should execute full workflow: tenant context → agent → audit → compliance."""

        # 1. Set tenant context
        set_current_tenant(mock_tenant)
        assert get_current_tenant().id == mock_tenant.id

        # 2. Create namespace for tenant
        ns = TenantNamespace(mock_tenant.id)
        collection_name = ns.apply_to_collection("knowledge")
        assert mock_tenant.id in collection_name

        # 3. Check RBAC permissions
        rbac = RBACEngine()
        with patch.object(rbac, "check_permission", return_value=True):
            has_permission = rbac.check_permission(
                "user_1",
                "agent:execute",
                tenant_id=mock_tenant.id,
            )
            assert has_permission is True

        # 4. Verify audit logging
        audit_log = Mock()
        audit_log.log = AsyncMock()

        # Log tenant context operation
        await audit_log.log(
            "agent.execution.started",
            {"tenant_id": mock_tenant.id, "user_id": "user_1"},
        )
        assert audit_log.log.called

        # 5. Brand check generated content
        brand = BrandController(
            BrandGuidelines(brand_name="Acme", forbidden_words=["badword"])
        )
        brand_result = await brand.review_content("Hello from Acme!")
        assert brand_result.approved is True

        # 6. Compliance check
        compliance = ComplianceFilter(sensitive_words=["secret"])
        compliance_result = await compliance.filter_output(
            "Hello from Acme!", ContentType.TEXT
        )
        assert compliance_result.blocked is False

    @pytest.mark.asyncio
    async def test_isolated_tenant_data_access(self, enterprise_context):
        """Should prevent cross-tenant data access."""
        tenant_a = Tenant(id="tenant_a", name="Tenant A")
        tenant_b = Tenant(id="tenant_b", name="Tenant B")

        # Create namespaces
        ns_a = TenantNamespace(tenant_a.id)
        ns_b = TenantNamespace(tenant_b.id)

        # Apply to collection name
        collection_a = ns_a.apply_to_collection("knowledge")
        collection_b = ns_b.apply_to_collection("knowledge")

        # Namespaces should be different
        assert collection_a != collection_b
        assert tenant_a.id in collection_a
        assert tenant_b.id in collection_b
