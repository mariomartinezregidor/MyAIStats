import csv
import io
import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from backend.app.core.auth import (
    create_session,
    get_current_user,
    hash_password,
    revoke_session,
    verify_password,
)
from backend.app.core.config import settings
from backend.app.core.security import vault
from backend.app.database.session import get_db
from backend.app.models.entities import (
    Account,
    AIModel,
    AppSetting,
    BalanceSnapshot,
    CostRecord,
    Credential,
    ExchangeRate,
    ModelPrice,
    Provider,
    SyncJob,
    UsageRecord,
    User,
)
from backend.app.schemas.api_schemas import (
    AccountConnectRequest,
    AccountOut,
    AccountTestResponse,
    AuthRegisterRequest,
    AuthTokenOut,
    AuthUserOut,
    BalanceItemOut,
    CostItemOut,
    CredentialRotateRequest,
    DashboardSummaryOut,
    DashboardTimelineOut,
    ModelPriceOut,
    PaginatedCostsOut,
    PaginatedUsageOut,
    ProviderOut,
    SettingsOut,
    SettingsUpdateRequest,
    SyncErrorOut,
    SyncJobOut,
    SyncStatusOut,
    TimelinePointOut,
    UsageItemOut,
    UserOut,
    UserUpdateRequest,
)
from backend.app.services.demo_service import (
    generate_demo_usage_and_costs,
    get_demo_accounts,
    get_demo_balances,
)
from backend.app.services.finance_service import (
    convert_amount,
    get_app_setting,
    get_default_currency,
    get_exchange_rate,
    is_demo_mode_enabled,
)
from backend.app.sync.manager import sync_manager
from connectors.base.types import ConnectorCredentials
from connectors.registry import get_connector

router = APIRouter(prefix="/api")


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user

PROVIDER_BILLING_URLS: dict[str, str] = {
    "openai": "https://platform.openai.com/settings/organization/billing",
    "openrouter": "https://openrouter.ai/credits",
    "anthropic": "https://console.anthropic.com/settings/billing",
    "deepseek": "https://platform.deepseek.com/top_up",
    "google": "https://console.cloud.google.com/billing",
    "groq": "https://console.groq.com/settings/billing",
    "mistral": "https://console.mistral.ai/billing",
    "together": "https://api.together.ai/settings/billing",
    "fireworks": "https://app.fireworks.ai/account/billing",
    "morph": "https://morphllm.com/",
    "refuseless": "https://refuseless.com/",
    "opencode": "https://opencode.ai/",
}


def _provider_billing_url(provider_id: str, fallback: str | None = None) -> str | None:
    url = PROVIDER_BILLING_URLS.get(provider_id)
    if url:
        return url
    return fallback

def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _resolve_date_range(
    preset: str | None,
    start_date: str | None,
    end_date: str | None,
) -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    if preset == "today":
        return today_start, today_end
    if preset == "7d":
        return today_start - timedelta(days=6), today_end
    if preset == "30d" or not preset:
        if not start_date and not end_date:
            return today_start - timedelta(days=29), today_end
    if preset == "current_month":
        return today_start.replace(day=1), today_end
    if preset == "previous_month":
        first_this_month = today_start.replace(day=1)
        last_prev_month = first_this_month - timedelta(seconds=1)
        first_prev_month = last_prev_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return first_prev_month, last_prev_month

    s_dt = today_start - timedelta(days=29)
    e_dt = today_end
    if start_date:
        try:
            s_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            if s_dt.tzinfo is None:
                s_dt = s_dt.replace(tzinfo=UTC)
        except ValueError:
            pass
    if end_date:
        try:
            e_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            if e_dt.tzinfo is None:
                e_dt = e_dt.replace(hour=23, minute=59, second=59, tzinfo=UTC)
        except ValueError:
            pass
    return s_dt, e_dt


@router.post("/register", response_model=AuthTokenOut, status_code=201, tags=["Auth"], include_in_schema=False)
@router.post("/signup", response_model=AuthTokenOut, status_code=201, tags=["Auth"], include_in_schema=False)
@router.post("/auth/signup", response_model=AuthTokenOut, status_code=201, tags=["Auth"], include_in_schema=False)
@router.post("/auth/register", response_model=AuthTokenOut, status_code=201, tags=["Auth"])
def register_user(
    payload: AuthRegisterRequest,
    db: Session = Depends(get_db),
) -> AuthTokenOut:
    if not settings.allow_registration:
        raise HTTPException(status_code=403, detail="Registration is disabled")
    email = payload.email.strip().lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=email, password_hash=hash_password(payload.password))
    # The first registered user becomes an admin when no admin exists yet.
    admin_count = db.scalar(select(func.count(User.id)).where(User.is_admin.is_(True)))
    if (admin_count or 0) == 0:
        user.is_admin = True
    db.add(user)
    db.commit()
    db.refresh(user)
    token, session = create_session(db, user)
    return AuthTokenOut(
        access_token=token,
        token_type="bearer",
        expires_at=session.expires_at,
        user=AuthUserOut(id=user.id, email=user.email, created_at=user.created_at, is_admin=user.is_admin),
    )


@router.post("/login", response_model=AuthTokenOut, tags=["Auth"], include_in_schema=False)
@router.post("/token", response_model=AuthTokenOut, tags=["Auth"], include_in_schema=False)
@router.post("/auth/token", response_model=AuthTokenOut, tags=["Auth"], include_in_schema=False)
@router.post("/signin", response_model=AuthTokenOut, tags=["Auth"], include_in_schema=False)
@router.post("/auth/login", response_model=AuthTokenOut, tags=["Auth"])
async def login_user(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthTokenOut:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)
    email = str(data.get("email") or data.get("username") or "").strip().lower()
    password = str(data.get("password") or "")
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is disabled")
    token, session = create_session(db, user)
    return AuthTokenOut(
        access_token=token,
        token_type="bearer",
        expires_at=session.expires_at,
        user=AuthUserOut(id=user.id, email=user.email, created_at=user.created_at, is_admin=user.is_admin),
    )


@router.get("/me", response_model=AuthUserOut, tags=["Auth"], include_in_schema=False)
@router.get("/user", response_model=AuthUserOut, tags=["Auth"], include_in_schema=False)
@router.get("/auth/me", response_model=AuthUserOut, tags=["Auth"])
@router.get("/users/me", response_model=AuthUserOut, tags=["Auth"], include_in_schema=False)
def auth_me(user: User = Depends(get_current_user)) -> AuthUserOut:
    return AuthUserOut(id=user.id, email=user.email, created_at=user.created_at, is_admin=user.is_admin)


@router.post("/auth/logout", tags=["Auth"])
def auth_logout(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    auth = request.headers.get("Authorization", "")
    token = auth.split(" ", 1)[1].strip() if auth.lower().startswith("bearer ") else ""
    if token:
        revoke_session(db, token)
    return {"status": "logged_out"}


@router.get("/users", response_model=list[UserOut], tags=["Users"])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> list[UserOut]:
    users = db.scalars(select(User).order_by(User.created_at)).all()
    return [
        UserOut(
            id=u.id,
            email=u.email,
            is_admin=u.is_admin,
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.put("/users/{user_id}", response_model=UserOut, tags=["Users"])
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> UserOut:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.is_admin is not None:
        # Prevent removing the last active admin.
        if target.is_admin and not payload.is_admin:
            admin_count = db.scalar(
                select(func.count(User.id)).where(User.is_admin.is_(True), User.is_active.is_(True))
            )
            if (admin_count or 0) <= 1:
                raise HTTPException(status_code=400, detail="Cannot remove the last admin")
        target.is_admin = payload.is_admin
    if payload.is_active is not None:
        if target.id == admin.id and not payload.is_active:
            raise HTTPException(status_code=400, detail="Cannot disable your own account")
        target.is_active = payload.is_active
    db.commit()
    db.refresh(target)
    return UserOut(
        id=target.id,
        email=target.email,
        is_admin=target.is_admin,
        is_active=target.is_active,
        created_at=target.created_at,
    )


@router.delete("/users/{user_id}", status_code=204, tags=["Users"])
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> Response:
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.is_admin:
        admin_count = db.scalar(
            select(func.count(User.id)).where(User.is_admin.is_(True))
        )
        if (admin_count or 0) <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last admin")
    db.delete(target)
    db.commit()
    return Response(status_code=204)


@router.get("/providers", response_model=list[ProviderOut], tags=["Providers"])
def list_providers(db: Session = Depends(get_db)) -> list[ProviderOut]:
    providers = db.scalars(
        select(Provider).order_by(Provider.category_priority, Provider.name)
    ).all()
    counts = dict(
        db.execute(
            select(Account.provider_id, func.count(Account.id)).group_by(Account.provider_id)
        ).all()
    )
    return [
        ProviderOut(
            id=p.id,
            name=p.name,
            category_priority=p.category_priority,
            api_base_url=p.api_base_url,
            docs_url=p.docs_url,
            billing_url=_provider_billing_url(p.id, p.docs_url),
            top_up_url=_provider_billing_url(p.id, p.docs_url),
            recharge_url=_provider_billing_url(p.id, p.docs_url),
            payment_url=_provider_billing_url(p.id, p.docs_url),
            auth_instructions=p.auth_instructions,
            supports_connection_test=p.supports_connection_test,
            supports_usage=p.supports_usage,
            supports_costs=p.supports_costs,
            supports_balance=p.supports_balance,
            supports_pricing=p.supports_pricing,
            requires_admin_key_for_usage=p.requires_admin_key_for_usage,
            capability_notes=p.capability_notes,
            connected_accounts_count=int(counts.get(p.id, 0)),
        )
        for p in providers
    ]


def _list_accounts(db: Session, user_id: int | None, include_demo: bool = True) -> list[AccountOut]:
    stmt = select(Account).order_by(Account.created_at.desc())
    if user_id is not None:
        stmt = stmt.where(Account.user_id == user_id)
    accounts = db.scalars(stmt).all()
    provider_map = {p.id: p.name for p in db.scalars(select(Provider)).all()}
    result: list[AccountOut] = []
    for acc in accounts:
        hint = acc.credential.masked_hint if acc.credential else "****"
        result.append(
            AccountOut(
                id=acc.id,
                provider_id=acc.provider_id,
                provider_name=provider_map.get(acc.provider_id, acc.provider_id),
                name=acc.name,
                external_org_id=acc.external_org_id,
                status=acc.status,
                status_message=acc.status_message,
                is_admin_key=acc.is_admin_key,
                masked_key_hint=hint,
                low_balance_threshold=acc.low_balance_threshold,
                last_sync_at=acc.last_sync_at,
                created_at=acc.created_at,
                is_demo=False,
            )
        )
    if include_demo and is_demo_mode_enabled(db):
        result.extend(get_demo_accounts())
    return result


@router.get("/accounts", response_model=list[AccountOut], tags=["Accounts"])
def list_accounts(
    include_demo: bool = Query(default=True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AccountOut]:
    return _list_accounts(db, user.id, include_demo)


@router.post("/accounts/connect", response_model=AccountOut, status_code=201, tags=["Accounts"])
async def connect_account(
    payload: AccountConnectRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AccountOut:
    provider = db.get(Provider, payload.provider_id.lower())
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{payload.provider_id}' not found")

    connector = get_connector(provider.id)
    creds_dto = ConnectorCredentials(
        api_key=payload.api_key,
        extra_secret=payload.extra_secret,
        organization_id=payload.organization_id,
        workspace_id=payload.workspace_id,
    )
    try:
        test_res = await connector.test_connection(creds_dto)
    except Exception as exc:
        test_res = None
        status_val = "error"
        status_msg = f"Connection check failed: {type(exc).__name__}"
        is_admin = False
    else:
        status_val = test_res.status if test_res.success else "error"
        status_msg = test_res.message
        is_admin = test_res.is_admin_key

    encrypted_key = vault.encrypt(payload.api_key.strip())
    encrypted_extra = (
        vault.encrypt(payload.extra_secret.strip()) if payload.extra_secret else None
    )
    masked = vault.mask_key(payload.api_key)

    account = Account(
        user_id=user.id,
        provider_id=provider.id,
        name=payload.name.strip(),
        external_org_id=payload.organization_id.strip() if payload.organization_id else None,
        external_workspace_id=payload.workspace_id.strip() if payload.workspace_id else None,
        status=status_val,
        status_message=status_msg,
        is_admin_key=is_admin,
        low_balance_threshold=payload.low_balance_threshold,
    )
    db.add(account)
    db.flush()

    credential = Credential(
        account_id=account.id,
        encrypted_api_key=encrypted_key,
        encrypted_extra_secret=encrypted_extra,
        masked_hint=masked,
        storage_backend="fernet_local",
    )
    db.add(credential)
    db.commit()
    db.refresh(account)

    return AccountOut(
        id=account.id,
        provider_id=account.provider_id,
        provider_name=provider.name,
        name=account.name,
        external_org_id=account.external_org_id,
        external_workspace_id=account.external_workspace_id,
        status=account.status,
        status_message=account.status_message,
        is_admin_key=account.is_admin_key,
        masked_key_hint=masked,
        low_balance_threshold=account.low_balance_threshold,
        last_sync_at=account.last_sync_at,
        created_at=account.created_at,
        is_demo=False,
    )


@router.put("/accounts/{account_id}/credentials", response_model=AccountOut, tags=["Accounts"])
async def rotate_account_credentials(
    account_id: int,
    payload: CredentialRotateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AccountOut:
    account = db.get(Account, account_id)
    if not account or not account.credential or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")

    account.credential.encrypted_api_key = vault.encrypt(payload.api_key.strip())
    account.credential.encrypted_extra_secret = (
        vault.encrypt(payload.extra_secret.strip()) if payload.extra_secret else None
    )
    account.credential.masked_hint = vault.mask_key(payload.api_key)
    if payload.organization_id is not None:
        account.external_org_id = payload.organization_id.strip() or None
    if payload.workspace_id is not None:
        account.external_workspace_id = payload.workspace_id.strip() or None

    db.commit()
    db.refresh(account)
    provider = db.get(Provider, account.provider_id)
    return AccountOut(
        id=account.id,
        provider_id=account.provider_id,
        provider_name=provider.name if provider else account.provider_id,
        name=account.name,
        external_org_id=account.external_org_id,
        external_workspace_id=account.external_workspace_id,
        status=account.status,
        status_message="Credentials rotated successfully.",
        is_admin_key=account.is_admin_key,
        masked_key_hint=account.credential.masked_hint,
        low_balance_threshold=account.low_balance_threshold,
        last_sync_at=account.last_sync_at,
        created_at=account.created_at,
        is_demo=False,
    )


@router.post("/accounts/{account_id}/test", response_model=AccountTestResponse, tags=["Accounts"])
async def test_account_connection(
    account_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AccountTestResponse:
    if account_id < 0:
        return AccountTestResponse(
            account_id=account_id,
            provider_id="demo",
            success=True,
            status="connected",
            message="[DEMO] Simulated account connection verified.",
            is_admin_key=True,
            warnings=[],
        )

    account = db.get(Account, account_id)
    if not account or not account.credential or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")

    connector = get_connector(account.provider_id)
    decrypted_key = vault.decrypt(account.credential.encrypted_api_key)
    decrypted_extra = (
        vault.decrypt(account.credential.encrypted_extra_secret)
        if account.credential.encrypted_extra_secret
        else None
    )
    creds = ConnectorCredentials(
        api_key=decrypted_key,
        extra_secret=decrypted_extra,
        organization_id=account.external_org_id,
        workspace_id=account.external_workspace_id,
    )
    try:
        res = await connector.test_connection(creds)
        account.status = res.status if res.success else "error"
        account.status_message = res.message
        account.is_admin_key = res.is_admin_key
        db.commit()
        return AccountTestResponse(
            account_id=account.id,
            provider_id=account.provider_id,
            success=res.success,
            status=account.status,
            message=res.message,
            is_admin_key=res.is_admin_key,
            warnings=res.warnings,
        )
    except Exception as exc:
        account.status = "error"
        account.status_message = f"Connection error: {type(exc).__name__}"
        db.commit()
        return AccountTestResponse(
            account_id=account.id,
            provider_id=account.provider_id,
            success=False,
            status="error",
            message=account.status_message,
            is_admin_key=False,
            warnings=[str(exc)],
        )


@router.post("/accounts/{account_id}/sync", response_model=SyncJobOut, tags=["Accounts"])
async def sync_account_endpoint(
    account_id: int,
    scope: str = Query(default="full"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SyncJobOut:
    if account_id < 0:
        now = datetime.now(UTC)
        return SyncJobOut(
            id=-1,
            account_id=account_id,
            provider_id="demo",
            scope=scope,
            status="completed",
            records_synced=25,
            started_at=now - timedelta(seconds=1),
            finished_at=now,
            message="[DEMO] Simulated synchronization completed.",
            errors=[],
        )

    account = db.get(Account, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")

    job = await sync_manager.sync_account(db, account_id, scope=scope)
    return _serialize_sync_job(job)


@router.delete("/accounts/{account_id}", status_code=204, tags=["Accounts"])
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    account = db.get(Account, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(account)
    db.commit()
    return Response(status_code=204)


def _collect_usage_items(
    db: Session,
    start_dt: datetime,
    end_dt: datetime,
    provider_id: str | None,
    account_id: int | None,
    model_id: str | None,
    display_currency: str,
    user_id: int | None = None,
) -> tuple[list[UsageItemOut], bool]:
    provider_map = {p.id: p.name for p in db.scalars(select(Provider)).all()}
    account_map = {a.id: a.name for a in db.scalars(select(Account)).all()}

    stmt = select(UsageRecord).where(
        UsageRecord.timestamp >= start_dt,
        UsageRecord.timestamp <= end_dt,
    )
    if provider_id:
        stmt = stmt.where(UsageRecord.provider_id == provider_id)
    if account_id and account_id > 0:
        stmt = stmt.where(UsageRecord.account_id == account_id)
    if model_id:
        stmt = stmt.where(UsageRecord.model_id == model_id)
    if user_id is not None:
        allowed_ids = [
            a.id for a in db.scalars(select(Account).where(Account.user_id == user_id)).all()
        ]
        if not allowed_ids:
            rows = []
            stmt = None
        else:
            stmt = stmt.where(UsageRecord.account_id.in_(allowed_ids))
    if stmt is not None:
        stmt = stmt.order_by(UsageRecord.timestamp.desc())
        rows = db.scalars(stmt).all() if (account_id is None or account_id > 0) else []
    else:
        rows = []
    items: list[UsageItemOut] = []
    for r in rows:
        conv_act, _, _ = convert_amount(db, r.actual_cost, r.currency, display_currency)
        conv_est, _, _ = convert_amount(db, r.estimated_cost, r.currency, display_currency)
        items.append(
            UsageItemOut(
                id=r.id,
                provider_id=r.provider_id,
                provider_name=provider_map.get(r.provider_id, r.provider_id),
                account_id=r.account_id,
                account_name=account_map.get(r.account_id, f"Account #{r.account_id}"),
                model_id=r.model_id,
                timestamp=_as_utc(r.timestamp) or r.timestamp,
                period_start=_as_utc(r.period_start) or r.period_start,
                period_end=_as_utc(r.period_end) or r.period_end,
                input_tokens=r.input_tokens,
                output_tokens=r.output_tokens,
                cached_input_tokens=r.cached_input_tokens,
                total_tokens=r.total_tokens,
                requests_count=r.requests_count,
                original_currency=r.currency,
                actual_cost=r.actual_cost,
                estimated_cost=r.estimated_cost,
                converted_actual_cost=conv_act,
                converted_estimated_cost=conv_est,
                display_currency=display_currency,
                cost_type=r.cost_type,
                data_source=r.data_source,
                data_precision=r.data_precision,
                is_demo=False,
            )
        )

    demo_active = is_demo_mode_enabled(db)
    if demo_active:
        demo_usage, _ = generate_demo_usage_and_costs(db, display_currency, start_dt, end_dt)
        for du in demo_usage:
            if provider_id and du.provider_id != provider_id:
                continue
            if account_id and du.account_id != account_id:
                continue
            if model_id and du.model_id != model_id:
                continue
            items.append(du)

    items.sort(key=lambda x: x.timestamp, reverse=True)
    return items, demo_active


@router.get("/usage", response_model=PaginatedUsageOut, tags=["Analytics"])
def get_usage(
    preset: str | None = Query(default="30d"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
    account_id: int | None = Query(default=None),
    model_id: str | None = Query(default=None),
    currency: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PaginatedUsageOut:
    display_currency = (currency or get_default_currency(db)).upper()
    start_dt, end_dt = _resolve_date_range(preset, start_date, end_date)
    items, demo_active = _collect_usage_items(
        db, start_dt, end_dt, provider_id, account_id, model_id, display_currency, user_id=user.id
    )
    total = len(items)
    offset = (page - 1) * page_size
    return PaginatedUsageOut(
        items=items[offset : offset + page_size],
        total=total,
        page=page,
        page_size=page_size,
        is_demo_included=demo_active,
    )


def _collect_cost_items(
    db: Session,
    start_dt: datetime,
    end_dt: datetime,
    provider_id: str | None,
    account_id: int | None,
    cost_type: str | None,
    display_currency: str,
    user_id: int | None = None,
) -> tuple[list[CostItemOut], bool]:
    provider_map = {p.id: p.name for p in db.scalars(select(Provider)).all()}
    account_map = {a.id: a.name for a in db.scalars(select(Account)).all()}

    stmt = select(CostRecord).where(
        CostRecord.period_start >= start_dt,
        CostRecord.period_start <= end_dt,
    )
    if provider_id:
        stmt = stmt.where(CostRecord.provider_id == provider_id)
    if account_id and account_id > 0:
        stmt = stmt.where(CostRecord.account_id == account_id)
    if cost_type in ("actual", "estimated"):
        stmt = stmt.where(CostRecord.cost_type == cost_type)
    if user_id is not None:
        allowed_ids = [
            a.id for a in db.scalars(select(Account).where(Account.user_id == user_id)).all()
        ]
        if not allowed_ids:
            rows = []
            stmt = None
        else:
            stmt = stmt.where(CostRecord.account_id.in_(allowed_ids))
    if stmt is not None:
        stmt = stmt.order_by(CostRecord.period_start.desc())
        rows = db.scalars(stmt).all() if (account_id is None or account_id > 0) else []
    else:
        rows = []
    items: list[CostItemOut] = []
    for r in rows:
        conv_amt, fx_rate, fx_date = convert_amount(db, r.amount, r.currency, display_currency)
        items.append(
            CostItemOut(
                id=r.id,
                provider_id=r.provider_id,
                provider_name=provider_map.get(r.provider_id, r.provider_id),
                account_id=r.account_id,
                account_name=account_map.get(r.account_id, f"Account #{r.account_id}"),
                model_id=r.model_id,
                period_start=_as_utc(r.period_start) or r.period_start,
                period_end=_as_utc(r.period_end) or r.period_end,
                amount=r.amount,
                original_currency=r.currency,
                converted_amount=conv_amt if conv_amt is not None else r.amount,
                display_currency=display_currency,
                exchange_rate_used=fx_rate,
                exchange_rate_date=fx_date,
                cost_type="actual" if r.cost_type == "actual" else "estimated",
                data_source=r.data_source,
                is_demo=False,
            )
        )

    demo_active = is_demo_mode_enabled(db)
    if demo_active:
        _, demo_costs = generate_demo_usage_and_costs(db, display_currency, start_dt, end_dt)
        for dc in demo_costs:
            if provider_id and dc.provider_id != provider_id:
                continue
            if account_id and dc.account_id != account_id:
                continue
            if cost_type in ("actual", "estimated") and dc.cost_type != cost_type:
                continue
            items.append(dc)

    items.sort(key=lambda x: x.period_start, reverse=True)
    return items, demo_active


@router.get("/costs", response_model=PaginatedCostsOut, tags=["Analytics"])
def get_costs(
    preset: str | None = Query(default="30d"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
    account_id: int | None = Query(default=None),
    cost_type: str | None = Query(default=None),
    currency: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PaginatedCostsOut:
    display_currency = (currency or get_default_currency(db)).upper()
    start_dt, end_dt = _resolve_date_range(preset, start_date, end_date)
    items, demo_active = _collect_cost_items(
        db, start_dt, end_dt, provider_id, account_id, cost_type, display_currency, user_id=user.id
    )
    actual_total = round(
        sum(i.converted_amount for i in items if i.cost_type == "actual"), 4
    )
    estimated_total = round(
        sum(i.converted_amount for i in items if i.cost_type == "estimated"), 4
    )
    total = len(items)
    offset = (page - 1) * page_size
    return PaginatedCostsOut(
        items=items[offset : offset + page_size],
        total=total,
        page=page,
        page_size=page_size,
        actual_total=actual_total,
        estimated_total=estimated_total,
        display_currency=display_currency,
        is_demo_included=demo_active,
    )


@router.get("/balances", response_model=list[BalanceItemOut], tags=["Balances"])
def get_balances(
    currency: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    user_id: int | None = None,
) -> list[BalanceItemOut]:
    display_currency = (currency or get_default_currency(db)).upper()
    effective_user_id = user_id if user_id is not None else (user.id if user is not None else None)
    stmt = select(Account).order_by(Account.id)
    if effective_user_id is not None:
        stmt = stmt.where(Account.user_id == effective_user_id)
    accounts = db.scalars(stmt).all()
    provider_map = {p.id: p for p in db.scalars(select(Provider)).all()}
    results: list[BalanceItemOut] = []

    for acc in accounts:
        prov = provider_map.get(acc.provider_id)
        latest_snap = db.scalar(
            select(BalanceSnapshot)
            .where(BalanceSnapshot.account_id == acc.id)
            .order_by(desc(BalanceSnapshot.captured_at))
            .limit(1)
        )
        is_supported = prov.supports_balance if prov else False
        if latest_snap:
            conv_bal, _, _ = convert_amount(
                db, latest_snap.available_balance, latest_snap.currency, display_currency
            )
            is_low = (
                acc.low_balance_threshold is not None
                and latest_snap.available_balance is not None
                and latest_snap.available_balance <= acc.low_balance_threshold
            )
            _billing = _provider_billing_url(acc.provider_id, prov.docs_url if prov else None)
            results.append(
                BalanceItemOut(
                    account_id=acc.id,
                    account_name=acc.name,
                    provider_id=acc.provider_id,
                    provider_name=prov.name if prov else acc.provider_id,
                    is_supported=latest_snap.is_supported,
                    available_balance=latest_snap.available_balance,
                    total_credits=latest_snap.total_credits,
                    used_credits=latest_snap.used_credits,
                    original_currency=latest_snap.currency,
                    converted_available_balance=conv_bal,
                    display_currency=display_currency,
                    low_balance_threshold=acc.low_balance_threshold,
                    is_low_balance=is_low,
                    status_note=latest_snap.status_note,
                    captured_at=latest_snap.captured_at,
                    is_demo=False,
                    billing_url=_billing,
                    top_up_url=_billing,
                    recharge_url=_billing,
                    payment_url=_billing,
                )
            )
        else:
            results.append(
                BalanceItemOut(
                    account_id=acc.id,
                    account_name=acc.name,
                    provider_id=acc.provider_id,
                    provider_name=prov.name if prov else acc.provider_id,
                    is_supported=is_supported,
                    available_balance=None,
                    total_credits=None,
                    used_credits=None,
                    original_currency="USD",
                    converted_available_balance=None,
                    display_currency=display_currency,
                    low_balance_threshold=acc.low_balance_threshold,
                    is_low_balance=False,
                    status_note=(
                        "Run account sync to fetch confirmed balance."
                        if is_supported
                        else "Balance endpoint is not supported by this provider's official API."
                    ),
                    captured_at=None,
                    is_demo=False,
                    billing_url=_provider_billing_url(acc.provider_id, prov.docs_url if prov else None),
                    top_up_url=_provider_billing_url(acc.provider_id, prov.docs_url if prov else None),
                    recharge_url=_provider_billing_url(acc.provider_id, prov.docs_url if prov else None),
                    payment_url=_provider_billing_url(acc.provider_id, prov.docs_url if prov else None),
                )
            )

    if is_demo_mode_enabled(db):
        demo_balances = get_demo_balances(db, display_currency)
        for b in demo_balances:
            _url = _provider_billing_url(b.provider_id)
            b.billing_url = _url
            b.top_up_url = _url
            b.recharge_url = _url
            b.payment_url = _url
        results.extend(demo_balances)
    return results


@router.get("/pricing", response_model=list[ModelPriceOut], tags=["Pricing"])
def get_pricing(
    provider_id: str | None = Query(default=None),
    include_history: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[ModelPriceOut]:
    provider_map = {p.id: p.name for p in db.scalars(select(Provider)).all()}
    model_map = {m.id: m for m in db.scalars(select(AIModel)).all()}

    stmt = select(ModelPrice)
    if not include_history:
        stmt = stmt.where(ModelPrice.is_current.is_(True))
    if provider_id:
        stmt = stmt.where(ModelPrice.provider_id == provider_id)
    stmt = stmt.order_by(ModelPrice.provider_id, ModelPrice.model_id, desc(ModelPrice.effective_from))
    prices = db.scalars(stmt).all()

    return [
        ModelPriceOut(
            id=p.id,
            provider_id=p.provider_id,
            provider_name=provider_map.get(p.provider_id, p.provider_id),
            model_id=p.model_id,
            display_name=(
                model_map[p.model_ref_id].display_name
                if p.model_ref_id in model_map
                else p.model_id
            ),
            context_window=(
                model_map[p.model_ref_id].context_window
                if p.model_ref_id in model_map
                else None
            ),
            input_price_per_million=p.input_price_per_million,
            output_price_per_million=p.output_price_per_million,
            cached_input_price_per_million=p.cached_input_price_per_million,
            currency=p.currency,
            price_source=p.price_source,
            effective_from=p.effective_from,
            recorded_at=p.recorded_at,
            is_current=p.is_current,
        )
        for p in prices
    ]


@router.get("/dashboard/summary", response_model=DashboardSummaryOut, tags=["Dashboard"])
def get_dashboard_summary(
    preset: str | None = Query(default="30d"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
    currency: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DashboardSummaryOut:
    display_currency = (currency or get_default_currency(db)).upper()
    start_dt, end_dt = _resolve_date_range(preset, start_date, end_date)
    usage_items, demo_active = _collect_usage_items(
        db, start_dt, end_dt, provider_id, None, None, display_currency, user_id=user.id
    )
    cost_items, _ = _collect_cost_items(
        db, start_dt, end_dt, provider_id, None, None, display_currency, user_id=user.id
    )
    balances = get_balances(currency=display_currency, db=db, user_id=user.id)
    if provider_id:
        balances = [b for b in balances if b.provider_id == provider_id]

    actual_cost = round(
        sum(c.converted_amount for c in cost_items if c.cost_type == "actual"), 4
    )
    estimated_cost = round(
        sum(c.converted_amount for c in cost_items if c.cost_type == "estimated"), 4
    )
    total_spending = round(actual_cost + estimated_cost, 4)

    confirmed_balance = round(
        sum(
            b.converted_available_balance or 0.0
            for b in balances
            if b.is_supported and b.converted_available_balance is not None
        ),
        4,
    )
    supported_bal_count = sum(
        1 for b in balances if b.is_supported and b.available_balance is not None
    )
    unsupported_bal_count = sum(1 for b in balances if not b.is_supported)

    in_tokens = sum(u.input_tokens for u in usage_items)
    out_tokens = sum(u.output_tokens for u in usage_items)
    cached_tokens = sum(u.cached_input_tokens for u in usage_items)

    # Aggregations by provider
    prov_agg: dict[str, dict] = {}
    for c in cost_items:
        entry = prov_agg.setdefault(
            c.provider_id,
            {
                "provider_id": c.provider_id,
                "provider_name": c.provider_name,
                "actual_cost": 0.0,
                "estimated_cost": 0.0,
                "total_cost": 0.0,
                "tokens": 0,
            },
        )
        if c.cost_type == "actual":
            entry["actual_cost"] = round(entry["actual_cost"] + c.converted_amount, 4)
        else:
            entry["estimated_cost"] = round(entry["estimated_cost"] + c.converted_amount, 4)
        entry["total_cost"] = round(entry["actual_cost"] + entry["estimated_cost"], 4)

    for u in usage_items:
        if u.provider_id in prov_agg:
            prov_agg[u.provider_id]["tokens"] += u.total_tokens

    # Aggregations by model
    model_agg: dict[str, dict] = {}
    for u in usage_items:
        entry = model_agg.setdefault(
            u.model_id,
            {
                "model_id": u.model_id,
                "provider_name": u.provider_name,
                "actual_cost": 0.0,
                "estimated_cost": 0.0,
                "total_cost": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cached_input_tokens": 0,
                "total_tokens": 0,
            },
        )
        act_c = u.converted_actual_cost or 0.0
        est_c = u.converted_estimated_cost or 0.0
        entry["actual_cost"] = round(entry["actual_cost"] + act_c, 4)
        entry["estimated_cost"] = round(entry["estimated_cost"] + est_c, 4)
        entry["total_cost"] = round(entry["actual_cost"] + entry["estimated_cost"], 4)
        entry["input_tokens"] += u.input_tokens
        entry["output_tokens"] += u.output_tokens
        entry["cached_input_tokens"] += u.cached_input_tokens
        entry["total_tokens"] += u.total_tokens

    all_accounts = _list_accounts(db, user.id if user is not None else None, include_demo=demo_active)
    fx_rate, fx_date, fx_source = get_exchange_rate(db, "USD", display_currency)

    return DashboardSummaryOut(
        display_currency=display_currency,
        exchange_rate_date=fx_date,
        exchange_rate_note=f"1 USD = {fx_rate} {display_currency} (source: {fx_source}, date: {fx_date})",
        actual_billed_cost=actual_cost,
        estimated_cost=estimated_cost,
        total_combined_spending=total_spending,
        confirmed_available_balance=confirmed_balance,
        supported_balance_accounts_count=supported_bal_count,
        unsupported_balance_accounts_count=unsupported_bal_count,
        input_tokens=in_tokens,
        output_tokens=out_tokens,
        cached_input_tokens=cached_tokens,
        total_tokens=in_tokens + out_tokens,
        connected_accounts_count=len(all_accounts),
        connected_providers_count=len({a.provider_id for a in all_accounts}),
        demo_mode_active=demo_active,
        spending_by_provider=sorted(
            prov_agg.values(), key=lambda x: x["total_cost"], reverse=True
        ),
        spending_by_model=sorted(
            model_agg.values(), key=lambda x: x["total_cost"], reverse=True
        ),
        recent_activity=usage_items[:12],
    )


@router.get("/dashboard/timeline", response_model=DashboardTimelineOut, tags=["Dashboard"])
def get_dashboard_timeline(
    preset: str | None = Query(default="30d"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    provider_id: str | None = Query(default=None),
    currency: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DashboardTimelineOut:
    display_currency = (currency or get_default_currency(db)).upper()
    start_dt, end_dt = _resolve_date_range(preset, start_date, end_date)
    usage_items, _ = _collect_usage_items(
        db, start_dt, end_dt, provider_id, None, None, display_currency, user_id=user.id
    )
    cost_items, _ = _collect_cost_items(
        db, start_dt, end_dt, provider_id, None, None, display_currency, user_id=user.id
    )
    balances = get_balances(currency=display_currency, db=db, user_id=user.id)
    base_balance = sum(
        b.converted_available_balance or 0.0
        for b in balances
        if b.is_supported and b.converted_available_balance is not None
    )

    daily_map: dict[str, dict] = {}
    cursor = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    while cursor <= end_dt:
        d_str = cursor.strftime("%Y-%m-%d")
        daily_map[d_str] = {
            "date": d_str,
            "actual_cost": 0.0,
            "estimated_cost": 0.0,
            "total_cost": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_input_tokens": 0,
        }
        cursor += timedelta(days=1)

    for c in cost_items:
        d_str = c.period_start.strftime("%Y-%m-%d")
        bucket = daily_map.get(d_str)
        if bucket:
            if c.cost_type == "actual":
                bucket["actual_cost"] = round(bucket["actual_cost"] + c.converted_amount, 4)
            else:
                bucket["estimated_cost"] = round(bucket["estimated_cost"] + c.converted_amount, 4)
            bucket["total_cost"] = round(bucket["actual_cost"] + bucket["estimated_cost"], 4)

    for u in usage_items:
        d_str = u.timestamp.strftime("%Y-%m-%d")
        bucket = daily_map.get(d_str)
        if bucket:
            bucket["input_tokens"] += u.input_tokens
            bucket["output_tokens"] += u.output_tokens
            bucket["cached_input_tokens"] += u.cached_input_tokens

    sorted_days = sorted(daily_map.values(), key=lambda x: x["date"])
    # Reconstruct balance trajectory from confirmed current balance + cumulative spend
    running_spend = sum(d["total_cost"] for d in sorted_days)
    daily_points: list[TimelinePointOut] = []
    for d in sorted_days:
        bal_val = round(base_balance + running_spend, 2) if base_balance > 0 else None
        running_spend = max(0.0, running_spend - d["total_cost"])
        daily_points.append(
            TimelinePointOut(
                date=d["date"],
                actual_cost=d["actual_cost"],
                estimated_cost=d["estimated_cost"],
                total_cost=d["total_cost"],
                input_tokens=d["input_tokens"],
                output_tokens=d["output_tokens"],
                cached_input_tokens=d["cached_input_tokens"],
                confirmed_balance=bal_val,
            )
        )

    monthly_map: dict[str, dict] = {}
    for p in daily_points:
        m_key = p.date[:7]
        m_bucket = monthly_map.setdefault(
            m_key,
            {
                "month": m_key,
                "actual_cost": 0.0,
                "estimated_cost": 0.0,
                "total_cost": 0.0,
                "tokens": 0,
            },
        )
        m_bucket["actual_cost"] = round(m_bucket["actual_cost"] + p.actual_cost, 4)
        m_bucket["estimated_cost"] = round(m_bucket["estimated_cost"] + p.estimated_cost, 4)
        m_bucket["total_cost"] = round(m_bucket["actual_cost"] + m_bucket["estimated_cost"], 4)
        m_bucket["tokens"] += p.input_tokens + p.output_tokens

    return DashboardTimelineOut(
        display_currency=display_currency,
        daily=daily_points,
        monthly=sorted(monthly_map.values(), key=lambda x: x["month"]),
    )


def _serialize_sync_job(job: SyncJob) -> SyncJobOut:
    return SyncJobOut(
        id=job.id,
        account_id=job.account_id,
        provider_id=job.provider_id,
        scope=job.scope,
        status=job.status,
        records_synced=job.records_synced,
        started_at=job.started_at,
        finished_at=job.finished_at,
        message=job.message,
        errors=[
            SyncErrorOut(
                id=err.id,
                provider_id=err.provider_id,
                account_id=err.account_id,
                capability=err.capability,
                error_code=err.error_code,
                error_message=err.error_message,
                created_at=err.created_at,
            )
            for err in job.errors
        ],
    )


@router.get("/sync/status", response_model=SyncStatusOut, tags=["Synchronization"])
def get_sync_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SyncStatusOut:
    user_account_ids = {
        a.id for a in db.scalars(select(Account).where(Account.user_id == user.id)).all()
    }
    jobs = db.scalars(
        select(SyncJob).order_by(desc(SyncJob.started_at)).limit(100)
    ).all()
    jobs = [j for j in jobs if j.account_id is None or j.account_id in user_account_ids][:20]
    recent_out = [_serialize_sync_job(j) for j in jobs]
    last_sync = jobs[0].finished_at or jobs[0].started_at if jobs else None

    if not recent_out and is_demo_mode_enabled(db):
        now = datetime.now(UTC)
        recent_out = [
            SyncJobOut(
                id=-1,
                account_id=-102,
                provider_id="openrouter",
                scope="full",
                status="completed",
                records_synced=31,
                started_at=now - timedelta(minutes=5, seconds=3),
                finished_at=now - timedelta(minutes=5),
                message="[DEMO] OpenRouter credits, models, and activity synchronized.",
                errors=[],
            ),
            SyncJobOut(
                id=-2,
                account_id=-101,
                provider_id="openai",
                scope="full",
                status="completed",
                records_synced=62,
                started_at=now - timedelta(minutes=8, seconds=4),
                finished_at=now - timedelta(minutes=8),
                message="[DEMO] OpenAI organization usage & cost buckets synchronized.",
                errors=[],
            ),
        ]
        last_sync = now - timedelta(minutes=5)

    return SyncStatusOut(
        is_running=sync_manager.is_running,
        last_sync_at=last_sync,
        usage_interval_minutes=int(get_app_setting(db, "sync_usage_interval_minutes", "15")),
        costs_interval_minutes=int(get_app_setting(db, "sync_costs_interval_minutes", "30")),
        balances_interval_minutes=int(get_app_setting(db, "sync_balances_interval_minutes", "30")),
        pricing_interval_minutes=int(get_app_setting(db, "sync_pricing_interval_minutes", "1440")),
        recent_jobs=recent_out,
    )


@router.post("/sync/run", response_model=list[SyncJobOut], tags=["Synchronization"])
async def trigger_global_sync(
    scope: str = Query(default="full"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SyncJobOut]:
    jobs = await sync_manager.sync_all_accounts(db, scope=scope, user_id=user.id)
    return [_serialize_sync_job(j) for j in jobs]


@router.get("/settings", response_model=SettingsOut, tags=["Settings"])
def get_settings_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SettingsOut:
    usd_eur, eff_date, source = get_exchange_rate(db, "USD", "EUR")
    eur_usd, _, _ = get_exchange_rate(db, "EUR", "USD")
    return SettingsOut(
        default_currency=get_default_currency(db),
        demo_mode=is_demo_mode_enabled(db),
        sync_usage_interval_minutes=int(get_app_setting(db, "sync_usage_interval_minutes", "15")),
        sync_costs_interval_minutes=int(get_app_setting(db, "sync_costs_interval_minutes", "30")),
        sync_balances_interval_minutes=int(
            get_app_setting(db, "sync_balances_interval_minutes", "30")
        ),
        sync_pricing_interval_minutes=int(
            get_app_setting(db, "sync_pricing_interval_minutes", "1440")
        ),
        usd_to_eur_rate=usd_eur,
        eur_to_usd_rate=eur_usd,
        exchange_rate_effective_date=eff_date,
        exchange_rate_source=source,
    )


@router.put("/settings", response_model=SettingsOut, tags=["Settings"])
def update_settings_endpoint(
    payload: SettingsUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SettingsOut:
    updates = {
        "default_currency": payload.default_currency.upper(),
        "demo_mode": "true" if payload.demo_mode else "false",
        "sync_usage_interval_minutes": str(payload.sync_usage_interval_minutes),
        "sync_costs_interval_minutes": str(payload.sync_costs_interval_minutes),
        "sync_balances_interval_minutes": str(payload.sync_balances_interval_minutes),
        "sync_pricing_interval_minutes": str(payload.sync_pricing_interval_minutes),
    }
    for k, v in updates.items():
        row = db.get(AppSetting, k)
        if row:
            row.value = v
        else:
            db.add(AppSetting(key=k, value=v))

    today_str = datetime.now(UTC).strftime("%Y-%m-%d")
    fx_usd_eur = db.scalar(
        select(ExchangeRate).where(
            ExchangeRate.base_currency == "USD",
            ExchangeRate.target_currency == "EUR",
            ExchangeRate.effective_date == today_str,
        )
    )
    if fx_usd_eur:
        fx_usd_eur.rate = payload.usd_to_eur_rate
        fx_usd_eur.source = "user_configured"
    else:
        db.add(
            ExchangeRate(
                base_currency="USD",
                target_currency="EUR",
                rate=payload.usd_to_eur_rate,
                effective_date=today_str,
                source="user_configured",
            )
        )

    fx_eur_usd = db.scalar(
        select(ExchangeRate).where(
            ExchangeRate.base_currency == "EUR",
            ExchangeRate.target_currency == "USD",
            ExchangeRate.effective_date == today_str,
        )
    )
    inv_rate = round(1.0 / payload.usd_to_eur_rate, 6)
    if fx_eur_usd:
        fx_eur_usd.rate = inv_rate
        fx_eur_usd.source = "user_configured"
    else:
        db.add(
            ExchangeRate(
                base_currency="EUR",
                target_currency="USD",
                rate=inv_rate,
                effective_date=today_str,
                source="user_configured",
            )
        )

    db.commit()
    return get_settings_endpoint(db)


@router.get("/export/{fmt}", tags=["Exports & Backups"])
def export_data(
    fmt: str,
    dataset: str = Query(default="usage", pattern="^(usage|costs|balances)$"),
    preset: str | None = Query(default="30d"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    fmt_clean = fmt.lower()
    if fmt_clean not in ("csv", "json"):
        raise HTTPException(status_code=400, detail="Unsupported export format. Use 'csv' or 'json'.")

    display_currency = get_default_currency(db)
    start_dt, end_dt = _resolve_date_range(preset, None, None)

    if dataset == "usage":
        items, _ = _collect_usage_items(db, start_dt, end_dt, None, None, None, display_currency, user_id=user.id)
        rows = [item.model_dump(mode="json") for item in items]
    elif dataset == "costs":
        items, _ = _collect_cost_items(db, start_dt, end_dt, None, None, None, display_currency, user_id=user.id)
        rows = [item.model_dump(mode="json") for item in items]
    else:
        items = get_balances(currency=display_currency, db=db, user_id=user.id)
        rows = [item.model_dump(mode="json") for item in items]

    filename = f"myaistats_{dataset}_{datetime.now(UTC).strftime('%Y%m%d')}.{fmt_clean}"
    if fmt_clean == "json":
        return Response(
            content=json.dumps(rows, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _sqlite_file_path() -> Path:
    if not settings.database_url.startswith("sqlite:///"):
        raise HTTPException(status_code=400, detail="Database backup is only supported for local SQLite.")
    raw = settings.database_url.replace("sqlite:///", "", 1)
    return Path(raw)


@router.get("/backup", tags=["Exports & Backups"])
def download_database_backup(
    user: User = Depends(get_current_user),
) -> FileResponse:
    db_path = _sqlite_file_path()
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="SQLite database file not found.")
    backup_dir = settings.data_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    snapshot_path = backup_dir / f"myaistats_backup_{ts}.db"
    shutil.copy2(db_path, snapshot_path)
    return FileResponse(
        path=snapshot_path,
        filename=snapshot_path.name,
        media_type="application/octet-stream",
    )


@router.post("/restore", tags=["Exports & Backups"])
async def restore_database_backup(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> dict:
    db_path = _sqlite_file_path()
    content = await file.read()
    if len(content) < 16 or not content.startswith(b"SQLite format 3\x00"):
        raise HTTPException(
            status_code=400,
            detail="Invalid backup file: uploaded file is not a valid SQLite 3 database.",
        )
    backup_dir = settings.data_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    pre_restore = backup_dir / f"pre_restore_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.db"
    if db_path.exists():
        shutil.copy2(db_path, pre_restore)
    db_path.write_bytes(content)
    return {"status": "restored", "bytes_written": len(content)}
