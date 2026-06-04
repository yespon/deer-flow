"""Admin management router for the DeerFlow admin dashboard.

Provides user CRUD, run monitoring, system stats, and aggregated dashboard endpoints.
Also provides read-only configuration introspection with API-key masking.
All routes require admin-level authentication (system_role == 'admin').
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import filelock
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from app.gateway.auth.password import hash_password
from app.gateway.deps import get_config
from deerflow.config.app_config import AppConfig, apply_logging_level, get_app_config
from deerflow.persistence.engine import get_session_factory
from deerflow.persistence.user.model import UserRow

logger = logging.getLogger(__name__)

# Config file lock to prevent concurrent write corruption
_CONFIG_LOCK_PATH = Path.home() / ".deer-flow" / "config.write.lock"
_CONFIG_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


async def _require_admin(request: Request) -> UserRow:
    from app.gateway.deps import get_current_user_from_request

    user = await get_current_user_from_request(request)
    if user.system_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UpdateUserRequest(BaseModel):
    email: EmailStr | None = None
    system_role: str | None = None


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8)


class UserResponse(BaseModel):
    id: str
    email: str
    system_role: str
    created_at: datetime
    oauth_provider: str | None
    token_version: int

    @classmethod
    def from_row(cls, row: UserRow) -> UserResponse:
        return cls(
            id=row.id,
            email=row.email,
            system_role=row.system_role,
            created_at=row.created_at,
            oauth_provider=row.oauth_provider,
            token_version=row.token_version,
        )


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int


class SystemStats(BaseModel):
    total_users: int
    total_runs: int
    total_threads: int
    total_feedback: int
    database_backend: str
    models: list[str]


@router.get("/users", response_model=PaginatedResponse)
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
):
    await _require_admin(request)
    sf = get_session_factory()
    if sf is None:
        raise HTTPException(status_code=503, detail="Database not available")
    async with sf() as session:
        base = select(UserRow)
        count_base = select(func.count(UserRow.id))
        if search:
            pattern = f"%{search}%"
            base = base.where(UserRow.email.ilike(pattern))
            count_base = count_base.where(UserRow.email.ilike(pattern))
        total = (await session.execute(count_base)).scalar_one()
        rows = (await session.execute(base.order_by(UserRow.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return PaginatedResponse(
        items=[UserResponse.from_row(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(request: Request, body: CreateUserRequest):
    await _require_admin(request)
    sf = get_session_factory()
    if sf is None:
        raise HTTPException(status_code=503, detail="Database not available")
    async with sf() as session:
        existing = (await session.execute(select(UserRow).where(UserRow.email == body.email))).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Email already exists")
        user = UserRow(
            id=str(uuid.uuid4()),
            email=body.email,
            password_hash=hash_password(body.password),
            system_role="user",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    await _write_audit_log(request, action="user_create", target_type="user", target_id=user.id, detail=f"Created user {body.email}")
    return UserResponse.from_row(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(request: Request, user_id: str, body: UpdateUserRequest):
    await _require_admin(request)
    sf = get_session_factory()
    if sf is None:
        raise HTTPException(status_code=503, detail="Database not available")
    async with sf() as session:
        user = (await session.execute(select(UserRow).where(UserRow.id == user_id))).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if body.email is not None:
            dup = (await session.execute(select(UserRow).where(UserRow.email == body.email, UserRow.id != user_id))).scalar_one_or_none()
            if dup:
                raise HTTPException(status_code=409, detail="Email already exists")
            user.email = body.email
        if body.system_role is not None:
            if body.system_role not in ("admin", "user"):
                raise HTTPException(status_code=400, detail="Invalid role")
            if user.system_role == "admin" and body.system_role != "admin":
                admin_count = (await session.execute(select(func.count(UserRow.id)).where(UserRow.system_role == "admin", UserRow.id != user_id))).scalar_one()
                if admin_count == 0:
                    raise HTTPException(status_code=400, detail="Cannot remove the last admin")
            user.system_role = body.system_role
        await session.commit()
        await session.refresh(user)
    await _write_audit_log(request, action="user_update", target_type="user", target_id=user_id, detail=f"Updated: email={body.email}, role={body.system_role}")
    return UserResponse.from_row(user)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(request: Request, user_id: str):
    admin = await _require_admin(request)
    sf = get_session_factory()
    if sf is None:
        raise HTTPException(status_code=503, detail="Database not available")
    async with sf() as session:
        user = (await session.execute(select(UserRow).where(UserRow.id == user_id))).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if str(user.id) == str(admin.id):
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        await session.delete(user)
        await session.commit()
    await _write_audit_log(request, action="user_delete", target_type="user", target_id=user_id, detail=f"Deleted user {user.email}")


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(request: Request, user_id: str, body: ResetPasswordRequest):
    await _require_admin(request)
    sf = get_session_factory()
    if sf is None:
        raise HTTPException(status_code=503, detail="Database not available")
    async with sf() as session:
        user = (await session.execute(select(UserRow).where(UserRow.id == user_id))).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.password_hash = hash_password(body.new_password)
        user.token_version += 1
        await session.commit()
    await _write_audit_log(request, action="password_reset", target_type="user", target_id=user_id, detail="Password reset by admin")
    return {"message": "Password reset successful"}


@router.get("/runs", response_model=PaginatedResponse)
async def list_runs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    user_id: str | None = Query(None),
):
    await _require_admin(request)
    from deerflow.persistence.run.model import RunRow

    sf = get_session_factory()
    if sf is None:
        raise HTTPException(status_code=503, detail="Database not available")
    async with sf() as session:
        base = select(RunRow)
        count_base = select(func.count(RunRow.run_id))
        if status:
            base = base.where(RunRow.status == status)
            count_base = count_base.where(RunRow.status == status)
        if user_id:
            base = base.where(RunRow.user_id == user_id)
            count_base = count_base.where(RunRow.user_id == user_id)
        total = (await session.execute(count_base)).scalar_one()
        rows = (await session.execute(base.order_by(RunRow.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return PaginatedResponse(
        items=[
            {
                "run_id": r.run_id,
                "thread_id": r.thread_id,
                "assistant_id": r.assistant_id,
                "user_id": r.user_id,
                "status": r.status,
                "model_name": r.model_name,
                "message_count": r.message_count,
                "total_tokens": r.total_tokens,
                "llm_call_count": r.llm_call_count,
                "first_human_message": r.first_human_message,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/threads", response_model=PaginatedResponse)
async def list_threads(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str | None = Query(None),
):
    await _require_admin(request)
    from deerflow.persistence.thread_meta.model import ThreadMetaRow

    sf = get_session_factory()
    if sf is None:
        raise HTTPException(status_code=503, detail="Database not available")
    async with sf() as session:
        base = select(ThreadMetaRow)
        count_base = select(func.count(ThreadMetaRow.thread_id))
        if user_id:
            base = base.where(ThreadMetaRow.user_id == user_id)
            count_base = count_base.where(ThreadMetaRow.user_id == user_id)
        total = (await session.execute(count_base)).scalar_one()
        rows = (await session.execute(base.order_by(ThreadMetaRow.updated_at.desc().nullslast()).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return PaginatedResponse(
        items=[
            {
                "thread_id": r.thread_id,
                "assistant_id": r.assistant_id,
                "user_id": r.user_id,
                "display_name": r.display_name,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(request: Request):
    await _require_admin(request)
    config = get_config(request)
    sf = get_session_factory()
    stats = {
        "total_users": 0,
        "total_runs": 0,
        "total_threads": 0,
        "total_feedback": 0,
        "database_backend": config.database.backend if config.database else "unknown",
        "models": [],
    }
    if sf is not None:
        from deerflow.persistence.feedback.model import FeedbackRow
        from deerflow.persistence.run.model import RunRow
        from deerflow.persistence.thread_meta.model import ThreadMetaRow

        async with sf() as session:
            stats["total_users"] = (await session.execute(select(func.count(UserRow.id)))).scalar_one()
            stats["total_runs"] = (await session.execute(select(func.count(RunRow.run_id)))).scalar_one()
            stats["total_threads"] = (await session.execute(select(func.count(ThreadMetaRow.thread_id)))).scalar_one()
            stats["total_feedback"] = (await session.execute(select(func.count(FeedbackRow.feedback_id)))).scalar_one()
    if config.models:
        stats["models"] = [m.name for m in config.models if m.name]
    return SystemStats(**stats)


@router.get("/feedback-stats")
async def get_feedback_stats(request: Request):
    await _require_admin(request)
    from deerflow.persistence.feedback.model import FeedbackRow

    sf = get_session_factory()
    if sf is None:
        raise HTTPException(status_code=503, detail="Database not available")
    async with sf() as session:
        total = (await session.execute(select(func.count(FeedbackRow.feedback_id)))).scalar_one()
        positive = (await session.execute(select(func.count(FeedbackRow.feedback_id)).where(FeedbackRow.rating > 0))).scalar_one()
        negative = (await session.execute(select(func.count(FeedbackRow.feedback_id)).where(FeedbackRow.rating < 0))).scalar_one()
    return {
        "total": total,
        "positive": positive,
        "negative": negative,
        "positive_rate": round(positive / total, 3) if total > 0 else 0,
    }


# ── Dashboard Aggregation ──────────────────────────────────────────────


class DashboardResponse(BaseModel):
    """Aggregated dashboard data for the admin overview page."""

    stats: SystemStats
    feedback_stats: dict[str, Any]
    channels: dict[str, Any]
    memory_config: dict[str, Any]
    skills_count: int
    mcp_servers: dict[str, Any]


class ConfigSectionInfo(BaseModel):
    """Metadata for one config section (read-only, for admin UI)."""

    key: str = Field(..., description="Section key in config.yaml, e.g. 'models', 'memory'")
    tier: int = Field(..., description="Hot-update tier: 1=hot-reload, 2=needs-restart, 3=security-sensitive")
    description: str = Field(default="", description="Human-readable section description")


class ConfigResponse(BaseModel):
    """Read-only config overview with tier annotations and masked secrets."""

    sections: list[ConfigSectionInfo] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict, description="Structured config dict with masked secrets")


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(request: Request):
    """Aggregated dashboard data: stats + channels + memory + skills + MCP."""
    await _require_admin(request)
    config = get_config(request)

    # Stats
    sf = get_session_factory()
    stats_dict: dict[str, Any] = {
        "total_users": 0,
        "total_runs": 0,
        "total_threads": 0,
        "total_feedback": 0,
        "database_backend": config.database.backend if config.database else "unknown",
        "models": [],
    }
    if sf is not None:
        from deerflow.persistence.feedback.model import FeedbackRow
        from deerflow.persistence.run.model import RunRow
        from deerflow.persistence.thread_meta.model import ThreadMetaRow

        async with sf() as session:
            stats_dict["total_users"] = (await session.execute(select(func.count(UserRow.id)))).scalar_one()
            stats_dict["total_runs"] = (await session.execute(select(func.count(RunRow.run_id)))).scalar_one()
            stats_dict["total_threads"] = (await session.execute(select(func.count(ThreadMetaRow.thread_id)))).scalar_one()
            stats_dict["total_feedback"] = (await session.execute(select(func.count(FeedbackRow.feedback_id)))).scalar_one()
    if config.models:
        stats_dict["models"] = [m.name for m in config.models if m.name]
    stats = SystemStats(**stats_dict)

    # Feedback stats
    feedback_stats: dict[str, Any] = {"total": 0, "positive": 0, "negative": 0, "positive_rate": 0}
    if sf is not None:
        from deerflow.persistence.feedback.model import FeedbackRow

        async with sf() as session:
            total = (await session.execute(select(func.count(FeedbackRow.feedback_id)))).scalar_one()
            positive = (await session.execute(select(func.count(FeedbackRow.feedback_id)).where(FeedbackRow.rating > 0))).scalar_one()
            negative = (await session.execute(select(func.count(FeedbackRow.feedback_id)).where(FeedbackRow.rating < 0))).scalar_one()
            feedback_stats = {"total": total, "positive": positive, "negative": negative, "positive_rate": round(positive / total, 3) if total > 0 else 0}

    # Channels
    channels: dict[str, Any] = {"service_running": False, "channels": {}}
    try:
        from app.channels.service import get_channel_service

        service = get_channel_service()
        if service is not None:
            channels = service.get_status()
    except Exception:
        pass

    # Memory config
    memory_config: dict[str, Any] = {}
    try:
        from deerflow.config.memory_config import get_memory_config

        mc = get_memory_config()
        memory_config = {"enabled": mc.enabled, "max_facts": mc.max_facts, "injection_enabled": mc.injection_enabled}
    except Exception:
        pass

    # Skills count
    skills_count = 0
    try:
        from deerflow.skills.storage import get_or_new_skill_storage

        storage = get_or_new_skill_storage(app_config=config)
        skills_count = len(storage.load_skills(enabled_only=False))
    except Exception:
        pass

    # MCP servers
    mcp_servers: dict[str, Any] = {}
    try:
        from deerflow.config.extensions_config import get_extensions_config

        ext = get_extensions_config()
        mcp_servers = {name: {"enabled": s.enabled, "type": getattr(s, "type", "stdio")} for name, s in ext.mcp_servers.items()}
    except Exception:
        pass

    return DashboardResponse(
        stats=stats,
        feedback_stats=feedback_stats,
        channels=channels,
        memory_config=memory_config,
        skills_count=skills_count,
        mcp_servers=mcp_servers,
    )


# ── Config Introspection (Read-Only) ───────────────────────────────────

_CONFIG_SECTIONS: list[dict[str, Any]] = [
    {"key": "models", "tier": 2, "description": "Available LLM models and their provider settings"},
    {"key": "tools", "tier": 2, "description": "Tool definitions and search configuration"},
    {"key": "tool_groups", "tier": 2, "description": "Tool group organization"},
    {"key": "tool_search", "tier": 1, "description": "Deferred tool loading via search"},
    {"key": "sandbox", "tier": 2, "description": "Sandbox provider and isolation settings"},
    {"key": "uploads", "tier": 2, "description": "Upload limits and conversion settings"},
    {"key": "memory", "tier": 1, "description": "Memory storage and injection settings"},
    {"key": "summarization", "tier": 2, "description": "Conversation summarization triggers and retention"},
    {"key": "loop_detection", "tier": 1, "description": "Loop detection thresholds and overrides"},
    {"key": "title", "tier": 2, "description": "Automatic conversation title generation"},
    {"key": "skills", "tier": 1, "description": "Skills directory and container mount path"},
    {"key": "channels", "tier": 2, "description": "IM channel integrations (Feishu, Slack, etc.)"},
    {"key": "subagents", "tier": 2, "description": "Subagent timeout and custom agent definitions"},
    {"key": "guardrails", "tier": 3, "description": "Pre-execution authorization for tool calls"},
    {"key": "circuit_breaker", "tier": 3, "description": "Circuit breaker for LLM call failure recovery"},
    {"key": "database", "tier": 3, "description": "Database backend and connection settings"},
    {"key": "run_events", "tier": 2, "description": "Run event storage backend and settings"},
    {"key": "agents_api", "tier": 3, "description": "Custom agent management API toggle"},
    {"key": "skill_evolution", "tier": 2, "description": "Agent-managed skill creation and improvement"},
    {"key": "token_usage", "tier": 1, "description": "Token usage collection and display"},
    {"key": "tenancy", "tier": 3, "description": "Multi-tenancy isolation and tenant config"},
    {"key": "rbac", "tier": 3, "description": "Role-based access control"},
    {"key": "audit", "tier": 3, "description": "Audit logging configuration"},
    {"key": "quota", "tier": 3, "description": "Resource quota management"},
    {"key": "approval", "tier": 3, "description": "Human-in-loop approval workflow"},
    {"key": "knowledge_base", "tier": 3, "description": "Enterprise knowledge base and RAG"},
    {"key": "brand", "tier": 3, "description": "Brand compliance checking"},
    {"key": "compliance", "tier": 3, "description": "Content compliance filtering"},
]

_SENSITIVE_KEY_SUFFIXES = ("api_key", "secret", "password", "token", "app_secret", "bot_token", "bot_secret", "client_secret")


def _mask_value(v: str) -> str:
    """Mask a sensitive string: show first 2 and last 2 chars, replace middle with ****."""
    if not v or len(v) <= 4:
        return "****"
    return f"{v[:2]}****{v[-2:]}"


def _mask_secrets(obj: Any) -> Any:
    """Recursively mask values whose keys look like secrets."""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            k_lower = k.lower()
            if any(s in k_lower for s in _SENSITIVE_KEY_SUFFIXES) and isinstance(v, str) and v:
                # Don't mask env-var references like $OPENAI_API_KEY
                if v.startswith("$"):
                    out[k] = v
                else:
                    out[k] = _mask_value(v)
            else:
                out[k] = _mask_secrets(v)
        return out
    if isinstance(obj, list):
        return [_mask_secrets(item) for item in obj]
    return obj


@router.get("/config", response_model=ConfigResponse)
async def get_admin_config(request: Request):
    """Read-only config introspection with tier annotations and masked secrets."""
    await _require_admin(request)
    config = get_config(request)

    raw = config.model_dump()
    masked = _mask_secrets(raw)

    sections = [ConfigSectionInfo(**s) for s in _CONFIG_SECTIONS]
    present_keys = set(raw.keys())
    sections = [s for s in sections if s.key in present_keys]

    return ConfigResponse(sections=sections, config=masked)


def _backup_config(config_path: Path) -> Path | None:
    """Create a timestamped backup of config.yaml before writing.
    Keeps at most 10 backups; oldest are pruned."""
    try:
        import shutil

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = config_path.parent / f"{config_path.name}.bak.{ts}"
        shutil.copy2(config_path, backup_path)
        # Prune old backups — keep newest 10
        backups = sorted(config_path.parent.glob(f"{config_path.name}.bak.*"))
        for old in backups[:-10]:
            old.unlink(missing_ok=True)
        return backup_path
    except Exception:
        logger.exception("Failed to create config backup")
        return None


class PendingRestartState:
    """Track whether a config change requiring restart has been made.
    In-memory flag; resets on server restart (which is the point)."""

    _pending: bool = False
    _pending_sections: list[str] = []
    _pending_since: datetime | None = None

    @classmethod
    def mark(cls, section: str) -> None:
        cls._pending = True
        if section not in cls._pending_sections:
            cls._pending_sections.append(section)
        cls._pending_since = datetime.now()

    @classmethod
    def clear(cls) -> None:
        cls._pending = False
        cls._pending_sections = []
        cls._pending_since = None

    @classmethod
    def status(cls) -> dict[str, Any]:
        return {
            "pending_restart": cls._pending,
            "sections": cls._pending_sections,
            "since": cls._pending_since.isoformat() if cls._pending_since else None,
        }


# ── Phase 3: Config Section Write ─────────────────────────────────────


class ConfigSectionUpdateRequest(BaseModel):
    """Request body for updating a config section."""

    section: str = Field(..., description="Section key, e.g. 'memory', 'title'")
    data: dict[str, Any] = Field(..., description="New section data (will be merged into config)")


class ConfigSectionUpdateResponse(BaseModel):
    """Response after a config section update."""

    success: bool
    tier: int
    message: str
    requires_restart: bool


@router.put("/config/{section}", response_model=ConfigSectionUpdateResponse)
async def update_config_section(
    request: Request,
    section: str,
    body: ConfigSectionUpdateRequest,
):
    """Update a specific config section. Tier 1 sections are hot-reloaded,
    Tier 2 sections require a restart, Tier 3 sections are blocked from API write."""
    await _require_admin(request)

    # Find tier
    section_meta = next((s for s in _CONFIG_SECTIONS if s["key"] == section), None)
    if section_meta is None:
        raise HTTPException(status_code=404, detail=f"Unknown config section: {section}")

    tier = section_meta["tier"]

    # Tier 3: block writes via API (security-sensitive, must edit file directly)
    if tier == 3:
        raise HTTPException(
            status_code=403,
            detail=f"Section '{section}' is security-sensitive (Tier 3). Edit config.yaml directly and restart the server.",
        )

    # Read the current config file
    import yaml

    from deerflow.config.app_config import reload_app_config

    config_path = Path(AppConfig.resolve_config_path())

    lock = filelock.FileLock(str(_CONFIG_LOCK_PATH), timeout=10)
    try:
        with lock:
            with open(config_path, encoding="utf-8") as f:
                raw_config = yaml.safe_load(f) or {}

            # Backup before modifying
            _backup_config(config_path)

            # Merge the section data
            raw_config[section] = body.data

            # Validate the merged config by constructing AppConfig
            try:
                AppConfig._normalize_nullable_defaults(raw_config)
                resolved = AppConfig.resolve_env_variables(raw_config)
                AppConfig._apply_database_defaults(resolved)
                AppConfig.model_validate(resolved)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid config data: {e}")

            # Write back to file
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(raw_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    except filelock.Timeout:
        raise HTTPException(status_code=409, detail="Config file is currently being modified by another request. Please retry.")

    # Tier 1: hot-reload
    requires_restart = tier >= 2
    if tier == 1:
        try:
            reload_app_config()
            request.app.state.config = get_app_config()
            request.app.state.config = get_app_config()
        except Exception:
            requires_restart = True

    # Tier 2: mark pending restart
    if requires_restart:
        PendingRestartState.mark(section)

    await _write_audit_log(request, action="config_update", target_type="config_section", target_id=section, detail=f"Tier {tier} update, restart={requires_restart}")

    return ConfigSectionUpdateResponse(
        success=True,
        tier=tier,
        message=f"Section '{section}' updated. {'Restart required.' if requires_restart else 'Hot-reloaded.'}",
        requires_restart=requires_restart,
    )


class ConfigValidateRequest(BaseModel):
    """Request body for config validation."""

    section: str
    data: dict[str, Any]


class ConfigValidateResponse(BaseModel):
    """Response for config validation."""

    valid: bool
    errors: list[str] = Field(default_factory=list)


@router.post("/config/validate", response_model=ConfigValidateResponse)
async def validate_config_section(request: Request, body: ConfigValidateRequest):
    """Pre-write validation: check if a section update would produce a valid config."""
    await _require_admin(request)

    import yaml

    config_path = Path(AppConfig.resolve_config_path())

    lock = filelock.FileLock(str(_CONFIG_LOCK_PATH), timeout=10)
    errors: list[str] = []
    try:
        with lock:
            with open(config_path, encoding="utf-8") as f:
                raw_config = yaml.safe_load(f) or {}

            # Merge proposed data (validate only, don't write)
            merged = {**raw_config}
            merged[body.section] = body.data

            AppConfig._normalize_nullable_defaults(merged)
            resolved = AppConfig.resolve_env_variables(merged)
            AppConfig._apply_database_defaults(resolved)
            AppConfig.model_validate(resolved)
    except filelock.Timeout:
        raise HTTPException(status_code=409, detail="Config file is currently locked. Please retry.")
    except Exception as e:
        errors.append(str(e))

    return ConfigValidateResponse(valid=len(errors) == 0, errors=errors)


# ── Phase 3: Restart ──────────────────────────────────────────────────


class RestartRequest(BaseModel):
    """Request body for graceful restart."""

    reason: str = Field(default="Admin requested restart", description="Reason for restart")


class RestartResponse(BaseModel):
    """Response for restart request."""

    success: bool
    message: str


@router.post("/restart", response_model=RestartResponse)
async def restart_server(request: Request, body: RestartRequest | None = None):
    """Trigger a graceful server restart. This reloads the config file
    and reinitializes the application state."""
    await _require_admin(request)

    reason = body.reason if body else "Admin requested restart"

    try:
        from deerflow.config.app_config import reload_app_config

        reload_app_config()
        new_config = get_app_config()
        request.app.state.config = new_config
        apply_logging_level(new_config.log_level)

        PendingRestartState.clear()
        await _write_audit_log(request, action="restart", target_type="server", detail=f"Server restart: {reason}")
        logger.info("Server restarted by admin: %s", reason)
        return RestartResponse(success=True, message=f"Server reloaded: {reason}")
    except Exception as e:
        logger.exception("Failed to restart server")
        raise HTTPException(status_code=500, detail=f"Restart failed: {e}")


@router.get("/restart/pending")
async def get_pending_restart(request: Request):
    """Check if there are config changes requiring a server restart."""
    await _require_admin(request)
    return PendingRestartState.status()


# ── Phase 3: Secrets / API Key Management ─────────────────────────────


class SecretEntry(BaseModel):
    """A masked secret entry."""

    key: str
    source: str = Field(description="Config section where this key was found")
    masked_value: str
    is_env_ref: bool = Field(description="True if value is an env-var reference like $OPENAI_API_KEY")


class SecretsListResponse(BaseModel):
    """List of all secret/config keys found in the config."""

    secrets: list[SecretEntry]


class SecretUpdateRequest(BaseModel):
    """Request body for updating a secret value."""

    key: str = Field(..., description="The dot-path to the key, e.g. 'models.0.api_key'")
    value: str = Field(..., description="New value (plain text, will be stored in config file)")


class SecretUpdateResponse(BaseModel):
    """Response after updating a secret."""

    success: bool
    message: str


def _collect_sections(obj: Any, path: str, results: list[dict], section_name: str) -> None:
    """Recursively find all sensitive keys in a config dict."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            k_lower = k.lower()
            current_path = f"{path}.{k}" if path else k
            if any(s in k_lower for s in _SENSITIVE_KEY_SUFFIXES) and isinstance(v, str) and v:
                is_env = v.startswith("$")
                results.append(
                    {
                        "key": current_path,
                        "source": section_name,
                        "masked_value": v if is_env else _mask_value(v),
                        "is_env_ref": is_env,
                    }
                )
            elif isinstance(v, (dict, list)):
                _collect_sections(v, current_path, results, section_name)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, dict):
                _collect_sections(item, f"{path}[{i}]", results, section_name)


@router.get("/secrets", response_model=SecretsListResponse)
async def list_secrets(request: Request):
    """List all sensitive keys across all config sections with masked values."""
    await _require_admin(request)
    config = get_config(request)
    raw = config.model_dump()

    results: list[dict] = []
    for section_key, section_data in raw.items():
        if isinstance(section_data, (dict, list)):
            _collect_sections(section_data, section_key, results, section_key)

    return SecretsListResponse(
        secrets=[SecretEntry(**r) for r in results],
    )


def _set_nested_key(obj: dict, dotted_key: str, value: str) -> bool:
    """Set a value in a nested dict using a dot-separated key path.
    Supports array indexing like 'models[0].api_key'."""
    parts = dotted_key.replace("[", ".").replace("]", "").split(".")
    current = obj
    for part in parts[:-1]:
        if part.isdigit():
            idx = int(part)
            if not isinstance(current, list) or idx >= len(current):
                return False
            current = current[idx]
        else:
            if part not in current:
                return False
            current = current[part]
    last = parts[-1]
    if isinstance(current, dict) and last in current:
        current[last] = value
        return True
    return False


@router.put("/secrets", response_model=SecretUpdateResponse)
async def update_secret(request: Request, body: SecretUpdateRequest):
    """Update a specific secret/API key in the config file.
    The value is written to config.yaml (not environment variables).
    For env-ref values ($VAR), the environment variable is updated instead
    if possible, otherwise the reference is replaced with the literal value."""
    await _require_admin(request)

    import yaml

    from deerflow.config.app_config import reload_app_config

    config_path = AppConfig.resolve_config_path()
    with open(config_path, encoding="utf-8") as f:
        raw_config = yaml.safe_load(f) or {}

    if not _set_nested_key(raw_config, body.key, body.value):
        raise HTTPException(status_code=400, detail=f"Could not set key '{body.key}' in config")

    # Write back
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(raw_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Reload
    try:
        reload_app_config()
        request.app.state.config = get_app_config()
    except Exception:
        pass

    await _write_audit_log(request, action="secret_update", target_type="secret", target_id=body.key, detail="Secret key updated")
    logger.info("Secret '%s' updated by admin", body.key)
    return SecretUpdateResponse(success=True, message=f"Secret '{body.key}' updated. Restart may be required.")


# ── Phase 4: Audit Log ────────────────────────────────────────────────

# uuid and datetime already imported at top of file


class AuditLogResponse(BaseModel):
    id: str
    user_id: str
    user_email: str
    action: str
    target_type: str
    target_id: str
    detail: str | None
    ip_address: str | None
    timestamp: datetime


async def _write_audit_log(
    request: Request,
    action: str,
    target_type: str,
    target_id: str = "",
    detail: str | None = None,
) -> None:
    """Write an audit log entry. Best-effort — never blocks the response."""
    try:
        from deerflow.persistence.audit.model import AuditLogRow

        admin = getattr(request.state, "admin_user", None)
        user_id = admin.id if admin else "system"
        user_email = admin.email if admin else "system"
        ip = request.client.host if request.client else None

        sf = get_session_factory()
        if sf is None:
            return
        async with sf() as session:
            row = AuditLogRow(
                id=str(uuid.uuid4()),
                user_id=user_id,
                user_email=user_email,
                action=action,
                target_type=target_type,
                target_id=target_id,
                detail=detail,
                ip_address=ip,
            )
            session.add(row)
            await session.commit()
    except Exception:
        logger.exception("Failed to write audit log")


@router.get("/audit")
async def list_audit_logs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str | None = Query(None),
    user_id: str | None = Query(None),
):
    """List audit log entries with optional filtering."""
    await _require_admin(request)
    from deerflow.persistence.audit.model import AuditLogRow

    sf = get_session_factory()
    if sf is None:
        raise HTTPException(status_code=503, detail="Database not available")
    async with sf() as session:
        base = select(AuditLogRow)
        count_base = select(func.count(AuditLogRow.id))
        if action:
            base = base.where(AuditLogRow.action == action)
            count_base = count_base.where(AuditLogRow.action == action)
        if user_id:
            base = base.where(AuditLogRow.user_id == user_id)
            count_base = count_base.where(AuditLogRow.user_id == user_id)
        total = (await session.execute(count_base)).scalar_one()
        rows = (await session.execute(base.order_by(AuditLogRow.timestamp.desc()).offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return PaginatedResponse(
        items=[
            AuditLogResponse(
                id=r.id,
                user_id=r.user_id,
                user_email=r.user_email,
                action=r.action,
                target_type=r.target_type,
                target_id=r.target_id,
                detail=r.detail,
                ip_address=r.ip_address,
                timestamp=r.timestamp,
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Phase 4: Enterprise Config Read ──────────────────────────────────


@router.get("/tenancy")
async def get_tenancy_config(request: Request):
    """Read tenancy configuration."""
    await _require_admin(request)
    config = get_config(request)
    return config.tenancy.model_dump()


@router.get("/rbac")
async def get_rbac_config(request: Request):
    """Read RBAC configuration."""
    await _require_admin(request)
    config = get_config(request)
    return config.rbac.model_dump()


@router.get("/approval")
async def get_approval_config(request: Request):
    """Read approval workflow configuration."""
    await _require_admin(request)
    config = get_config(request)
    return config.approval.model_dump()


@router.get("/knowledge-base")
async def get_knowledge_base_config(request: Request):
    """Read knowledge base configuration."""
    await _require_admin(request)
    config = get_config(request)
    return config.knowledge_base.model_dump()


@router.get("/brand")
async def get_brand_config(request: Request):
    """Read brand compliance configuration."""
    await _require_admin(request)
    config = get_config(request)
    return config.brand.model_dump()


@router.get("/compliance")
async def get_compliance_config(request: Request):
    """Read content compliance configuration."""
    await _require_admin(request)
    config = get_config(request)
    return config.compliance.model_dump()


@router.get("/quota")
async def get_quota_config(request: Request):
    """Read quota management configuration."""
    await _require_admin(request)
    config = get_config(request)
    return config.quota.model_dump()


# ── Phase 4: Enterprise Config Write ─────────────────────────────────


class EnterpriseConfigUpdateRequest(BaseModel):
    """Request body for updating an enterprise config section."""

    data: dict[str, Any] = Field(..., description="New section data")


async def _update_enterprise_section(request: Request, section: str, data: dict[str, Any]) -> dict[str, Any]:
    """Common handler for enterprise section updates.
    Uses the same lock + backup + audit pattern as core config writes."""
    import yaml

    from deerflow.config.app_config import reload_app_config

    config_path = Path(AppConfig.resolve_config_path())
    lock = filelock.FileLock(str(_CONFIG_LOCK_PATH), timeout=10)

    try:
        with lock:
            with open(config_path, encoding="utf-8") as f:
                raw_config = yaml.safe_load(f) or {}

            _backup_config(config_path)
            raw_config[section] = data

            # Validate
            try:
                AppConfig._normalize_nullable_defaults(raw_config)
                resolved = AppConfig.resolve_env_variables(raw_config)
                AppConfig._apply_database_defaults(resolved)
                AppConfig.model_validate(resolved)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid config data: {e}")

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(raw_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    except filelock.Timeout:
        raise HTTPException(status_code=409, detail="Config file is currently locked. Please retry.")

    # Hot-reload for applicable sections, mark pending for others
    try:
        reload_app_config()
        request.app.state.config = get_app_config()
    except Exception:
        PendingRestartState.mark(section)

    await _write_audit_log(request, action="enterprise_config_update", target_type="config_section", target_id=section, detail=f"Enterprise section '{section}' updated")

    return {"success": True, "message": f"Section '{section}' updated. Restart may be required."}


@router.put("/tenancy")
async def update_tenancy_config(request: Request, body: EnterpriseConfigUpdateRequest):
    """Update tenancy configuration (requires admin + audit)."""
    await _require_admin(request)
    return await _update_enterprise_section(request, "tenancy", body.data)


@router.put("/rbac")
async def update_rbac_config(request: Request, body: EnterpriseConfigUpdateRequest):
    """Update RBAC configuration (requires admin + audit)."""
    await _require_admin(request)
    return await _update_enterprise_section(request, "rbac", body.data)


@router.put("/approval")
async def update_approval_config(request: Request, body: EnterpriseConfigUpdateRequest):
    """Update approval workflow configuration (requires admin + audit)."""
    await _require_admin(request)
    return await _update_enterprise_section(request, "approval", body.data)


@router.put("/knowledge-base")
async def update_knowledge_base_config(request: Request, body: EnterpriseConfigUpdateRequest):
    """Update knowledge base configuration (requires admin + audit)."""
    await _require_admin(request)
    return await _update_enterprise_section(request, "knowledge_base", body.data)


@router.put("/brand")
async def update_brand_config(request: Request, body: EnterpriseConfigUpdateRequest):
    """Update brand compliance configuration (requires admin + audit)."""
    await _require_admin(request)
    return await _update_enterprise_section(request, "brand", body.data)


@router.put("/compliance")
async def update_compliance_config(request: Request, body: EnterpriseConfigUpdateRequest):
    """Update content compliance configuration (requires admin + audit)."""
    await _require_admin(request)
    return await _update_enterprise_section(request, "compliance", body.data)


@router.put("/quota")
async def update_quota_config(request: Request, body: EnterpriseConfigUpdateRequest):
    """Update quota management configuration (requires admin + audit)."""
    await _require_admin(request)
    return await _update_enterprise_section(request, "quota", body.data)
