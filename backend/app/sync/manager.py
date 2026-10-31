import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.security import vault
from backend.app.database.session import SessionLocal
from backend.app.models.entities import (
    Account,
    BalanceSnapshot,
    CostRecord,
    SyncError,
    SyncJob,
    UsageRecord,
)
from backend.app.services.finance_service import estimate_cost_from_pricing, get_app_setting
from backend.app.services.seed_service import upsert_model_price
from connectors.base.types import ConnectorCredentials
from connectors.registry import get_connector, list_connectors


class SyncManager:
    """
    Handles idempotent account synchronization, prevents concurrent duplicate jobs,
    isolates errors per provider/account, and avoids double counting actual vs estimated costs.
    """

    def __init__(self) -> None:
        self._active_account_locks: set[int] = set()
        self._global_lock = asyncio.Lock()
        self._bg_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    @property
    def is_running(self) -> bool:
        return bool(self._active_account_locks) or self._global_lock.locked()

    async def sync_account(
        self,
        db: Session,
        account_id: int,
        scope: str = "full",
        days_back: int = 30,
    ) -> SyncJob:
        if account_id in self._active_account_locks:
            existing_job = db.scalar(
                select(SyncJob)
                .where(SyncJob.account_id == account_id, SyncJob.status == "running")
                .order_by(SyncJob.started_at.desc())
            )
            if existing_job:
                return existing_job

        self._active_account_locks.add(account_id)
        account = db.get(Account, account_id)
        if not account or not account.credential:
            self._active_account_locks.discard(account_id)
            raise ValueError(f"Account {account_id} or its credential not found")

        job = SyncJob(
            account_id=account.id,
            provider_id=account.provider_id,
            scope=scope,
            status="running",
            records_synced=0,
            started_at=datetime.now(UTC),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        records_synced = 0
        errors_count = 0
        try:
            connector = get_connector(account.provider_id)
            caps = connector.get_capabilities()
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

            end_time = datetime.now(UTC)
            start_time = end_time - timedelta(days=days_back)

            # 1. Pricing sync
            if scope in ("full", "pricing") and caps.supports_pricing:
                try:
                    prices = await connector.fetch_model_pricing(creds)
                    for p in prices:
                        upsert_model_price(db, account.provider_id, p)
                        records_synced += 1
                    db.commit()
                except Exception as exc:
                    errors_count += 1
                    self._record_error(db, job.id, account.provider_id, account.id, "pricing", exc)

            # 2. Official Costs sync (run before Usage so we know if official actual costs exist for a date)
            actual_cost_dates: set[str] = set()
            if scope in ("full", "costs") and caps.supports_costs:
                try:
                    cost_dtos = await connector.fetch_costs(creds, start_time, end_time)
                    for c_dto in cost_dtos:
                        day_key = c_dto.period_start.strftime("%Y-%m-%d")
                        actual_cost_dates.add(day_key)
                        existing_cost = db.scalar(
                            select(CostRecord).where(
                                CostRecord.account_id == account.id,
                                CostRecord.external_record_id == c_dto.external_record_id,
                            )
                        )
                        if existing_cost:
                            existing_cost.amount = c_dto.amount
                            existing_cost.currency = c_dto.currency
                        else:
                            db.add(
                                CostRecord(
                                    provider_id=account.provider_id,
                                    account_id=account.id,
                                    model_id=c_dto.model_id,
                                    period_start=c_dto.period_start,
                                    period_end=c_dto.period_end,
                                    amount=c_dto.amount,
                                    currency=c_dto.currency,
                                    cost_type="actual",
                                    data_source=c_dto.data_source,
                                    external_record_id=c_dto.external_record_id,
                                )
                            )
                            records_synced += 1
                    db.commit()
                except Exception as exc:
                    errors_count += 1
                    self._record_error(db, job.id, account.provider_id, account.id, "costs", exc)

            # 3. Usage sync & non-double-counted cost estimation
            if scope in ("full", "usage") and caps.supports_usage:
                try:
                    usage_dtos = await connector.fetch_usage(creds, start_time, end_time)
                    for u_dto in usage_dtos:
                        day_key = u_dto.period_start.strftime("%Y-%m-%d")
                        est_cost: float | None = None
                        cost_type = "actual" if u_dto.actual_cost is not None else "estimated"

                        if u_dto.actual_cost is None:
                            est_val, _ = estimate_cost_from_pricing(
                                db,
                                account.provider_id,
                                u_dto.model_id,
                                u_dto.input_tokens,
                                u_dto.output_tokens,
                                u_dto.cached_input_tokens,
                            )
                            est_cost = est_val
                            cost_type = "estimated" if est_val is not None else "none"

                        existing_usage = db.scalar(
                            select(UsageRecord).where(
                                UsageRecord.account_id == account.id,
                                UsageRecord.external_record_id == u_dto.external_record_id,
                            )
                        )
                        if existing_usage:
                            existing_usage.input_tokens = u_dto.input_tokens
                            existing_usage.output_tokens = u_dto.output_tokens
                            existing_usage.cached_input_tokens = u_dto.cached_input_tokens
                            existing_usage.total_tokens = u_dto.total_tokens
                            existing_usage.requests_count = u_dto.requests_count
                            existing_usage.actual_cost = u_dto.actual_cost
                            existing_usage.estimated_cost = est_cost
                            existing_usage.cost_type = cost_type
                        else:
                            db.add(
                                UsageRecord(
                                    provider_id=account.provider_id,
                                    account_id=account.id,
                                    model_id=u_dto.model_id,
                                    timestamp=u_dto.timestamp,
                                    period_start=u_dto.period_start,
                                    period_end=u_dto.period_end,
                                    input_tokens=u_dto.input_tokens,
                                    output_tokens=u_dto.output_tokens,
                                    cached_input_tokens=u_dto.cached_input_tokens,
                                    total_tokens=u_dto.total_tokens,
                                    requests_count=u_dto.requests_count,
                                    currency=u_dto.currency,
                                    actual_cost=u_dto.actual_cost,
                                    estimated_cost=est_cost,
                                    cost_type=cost_type,
                                    data_source=u_dto.data_source,
                                    data_precision=u_dto.data_precision,
                                    external_record_id=u_dto.external_record_id,
                                )
                            )
                            records_synced += 1

                        # Avoid double counting: only create an estimated CostRecord if the provider did NOT
                        # already supply an official actual billing record for that date.
                        if (
                            u_dto.actual_cost is None
                            and est_cost is not None
                            and est_cost > 0
                            and day_key not in actual_cost_dates
                        ):
                            est_ext_id = f"est-cost-{u_dto.external_record_id}"
                            existing_est = db.scalar(
                                select(CostRecord).where(
                                    CostRecord.account_id == account.id,
                                    CostRecord.external_record_id == est_ext_id,
                                )
                            )
                            if existing_est:
                                existing_est.amount = est_cost
                            else:
                                db.add(
                                    CostRecord(
                                        provider_id=account.provider_id,
                                        account_id=account.id,
                                        model_id=u_dto.model_id,
                                        period_start=u_dto.period_start,
                                        period_end=u_dto.period_end,
                                        amount=est_cost,
                                        currency=u_dto.currency,
                                        cost_type="estimated",
                                        data_source="usage_price_estimation",
                                        external_record_id=est_ext_id,
                                    )
                                )
                    db.commit()
                except Exception as exc:
                    errors_count += 1
                    self._record_error(db, job.id, account.provider_id, account.id, "usage", exc)

            # 4. Balance sync
            if scope in ("full", "balances"):
                try:
                    bal_dto = await connector.fetch_balance(creds)
                    db.add(
                        BalanceSnapshot(
                            provider_id=account.provider_id,
                            account_id=account.id,
                            available_balance=bal_dto.available_balance,
                            total_credits=bal_dto.total_credits,
                            used_credits=bal_dto.used_credits,
                            currency=bal_dto.currency,
                            is_supported=bal_dto.is_supported,
                            status_note=bal_dto.status_note,
                            data_source=bal_dto.data_source,
                        )
                    )
                    if bal_dto.is_supported and bal_dto.available_balance is not None:
                        records_synced += 1
                    db.commit()
                except Exception as exc:
                    errors_count += 1
                    self._record_error(db, job.id, account.provider_id, account.id, "balances", exc)

            now_utc = datetime.now(UTC)
            account.last_sync_at = now_utc
            if errors_count == 0:
                account.status = "connected"
                job.status = "completed"
                job.message = f"Synchronized {records_synced} records."
            else:
                job.status = "partial"
                job.message = f"Synchronized {records_synced} records with {errors_count} isolated warning(s)."
            job.records_synced = records_synced
            job.finished_at = now_utc
            db.commit()
            db.refresh(job)
            return job
        except Exception as exc:
            job.status = "failed"
            job.finished_at = datetime.now(UTC)
            job.message = str(exc)
            self._record_error(db, job.id, account.provider_id, account.id, scope, exc)
            db.commit()
            db.refresh(job)
            return job
        finally:
            self._active_account_locks.discard(account_id)

    async def sync_all_accounts(
        self, db: Session, scope: str = "full", user_id: int | None = None
    ) -> list[SyncJob]:
        """Synchronizes all connected accounts, isolating failures between providers/accounts."""
        if self._global_lock.locked():
            return []
        async with self._global_lock:
            stmt = select(Account)
            if user_id is not None:
                stmt = stmt.where(Account.user_id == user_id)
            accounts = db.scalars(stmt).all()
            jobs: list[SyncJob] = []
            for acc in accounts:
                try:
                    j = await self.sync_account(db, acc.id, scope=scope)
                    jobs.append(j)
                except Exception:
                    continue
            return jobs

    def _record_error(
        self,
        db: Session,
        job_id: int,
        provider_id: str,
        account_id: int | None,
        capability: str,
        exc: Exception,
    ) -> None:
        db.add(
            SyncError(
                sync_job_id=job_id,
                provider_id=provider_id,
                account_id=account_id,
                capability=capability,
                error_code=type(exc).__name__,
                error_message=str(exc)[:500],
            )
        )
        db.commit()

    def start_background_loop(self) -> None:
        if self._bg_task is None or self._bg_task.done():
            self._stop_event.clear()
            self._bg_task = asyncio.create_task(self._scheduler_loop())

    async def stop_background_loop(self) -> None:
        self._stop_event.set()
        if self._bg_task and not self._bg_task.done():
            self._bg_task.cancel()
            try:
                await self._bg_task
            except asyncio.CancelledError:
                pass

    async def _scheduler_loop(self) -> None:
        last_usage = datetime.now(UTC)
        last_costs = datetime.now(UTC)
        last_balances = datetime.now(UTC)
        last_pricing = datetime.now(UTC)

        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(60)
                now = datetime.now(UTC)
                with SessionLocal() as db:
                    u_int = int(get_app_setting(db, "sync_usage_interval_minutes", "15"))
                    c_int = int(get_app_setting(db, "sync_costs_interval_minutes", "30"))
                    b_int = int(get_app_setting(db, "sync_balances_interval_minutes", "30"))
                    p_int = int(get_app_setting(db, "sync_pricing_interval_minutes", "1440"))

                    if (now - last_usage).total_seconds() >= u_int * 60:
                        await self.sync_all_accounts(db, scope="usage")
                        last_usage = now
                    if (now - last_costs).total_seconds() >= c_int * 60:
                        await self.sync_all_accounts(db, scope="costs")
                        last_costs = now
                    if (now - last_balances).total_seconds() >= b_int * 60:
                        await self.sync_all_accounts(db, scope="balances")
                        last_balances = now
                    if (now - last_pricing).total_seconds() >= p_int * 60:
                        for conn in list_connectors():
                            prices = await conn.fetch_model_pricing(None)
                            for p in prices:
                                upsert_model_price(db, conn.provider_id, p)
                        db.commit()
                        last_pricing = now
            except asyncio.CancelledError:
                break
            except Exception:
                continue


sync_manager = SyncManager()
