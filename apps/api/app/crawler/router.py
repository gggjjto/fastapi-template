from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from hatchet_sdk import Hatchet

from app.core.openapi import error_responses
from app.core.pagination import Page, Pagination
from app.core.response import ApiResponse
from app.crawler.application.service import CrawlerService, CrawlRunCanceller
from app.crawler.domain.constants import CrawlJobStatus
from app.crawler.domain.schemas import (
    CrawlHandlerRead,
    CrawlJobCreate,
    CrawlJobRead,
    CrawlMetrics,
    CrawlRunCreate,
    CrawlTargetCreate,
    CrawlTargetRead,
    CrawlTargetUpdate,
)
from app.crawler.runtime.registry import discover_handlers, registry
from app.db.session import DBSession
from app.tenants.constants import TenantRole
from app.tenants.dependencies import RequireTenantRole

router = APIRouter()
discover_handlers()


def get_crawl_run_canceller() -> CrawlRunCanceller | None:
    if not os.getenv("HATCHET_CLIENT_TOKEN"):
        return None
    return Hatchet().runs


@router.get(
    "/targets",
    response_model=ApiResponse[Page[CrawlTargetRead]],
    dependencies=[Depends(RequireTenantRole())],
    summary="List crawl targets",
    description="List active crawl targets belonging to the selected tenant.",
)
async def list_targets(
    tenant_id: uuid.UUID, session: DBSession, pagination: Pagination
) -> ApiResponse[Page[CrawlTargetRead]]:
    targets, total = await CrawlerService(session).list_targets(
        tenant_id=tenant_id, limit=pagination.limit, offset=pagination.offset
    )
    return ApiResponse.ok(
        Page(
            items=[CrawlTargetRead.model_validate(target) for target in targets],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )
    )


@router.post(
    "/targets",
    response_model=ApiResponse[CrawlTargetRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequireTenantRole(TenantRole.OWNER, TenantRole.ADMIN))],
    summary="Create crawl target",
    description="Create a tenant-scoped HTTP target with an optional Cron schedule.",
)
async def create_target(
    tenant_id: uuid.UUID, payload: CrawlTargetCreate, session: DBSession
) -> ApiResponse[CrawlTargetRead]:
    target = await CrawlerService(session).create_target(tenant_id=tenant_id, payload=payload)
    return ApiResponse.ok(CrawlTargetRead.model_validate(target))


@router.get(
    "/targets/{target_id}",
    response_model=ApiResponse[CrawlTargetRead],
    dependencies=[Depends(RequireTenantRole())],
    summary="Get crawl target",
    description="Get one tenant-scoped crawl target.",
)
async def get_target(
    tenant_id: uuid.UUID, target_id: uuid.UUID, session: DBSession
) -> ApiResponse[CrawlTargetRead]:
    target = await CrawlerService(session).get_target(tenant_id=tenant_id, target_id=target_id)
    return ApiResponse.ok(CrawlTargetRead.model_validate(target))


@router.patch(
    "/targets/{target_id}",
    response_model=ApiResponse[CrawlTargetRead],
    dependencies=[Depends(RequireTenantRole(TenantRole.OWNER, TenantRole.ADMIN))],
    summary="Update crawl target",
    description="Update a target and recompute its next scheduled run.",
)
async def update_target(
    tenant_id: uuid.UUID,
    target_id: uuid.UUID,
    payload: CrawlTargetUpdate,
    session: DBSession,
) -> ApiResponse[CrawlTargetRead]:
    target = await CrawlerService(session).update_target(
        tenant_id=tenant_id, target_id=target_id, payload=payload
    )
    return ApiResponse.ok(CrawlTargetRead.model_validate(target))


@router.post(
    "/targets/{target_id}/archive",
    response_model=ApiResponse[CrawlTargetRead],
    dependencies=[Depends(RequireTenantRole(TenantRole.OWNER, TenantRole.ADMIN))],
    summary="Archive crawl target",
    description="Disable and archive a target while retaining its job history.",
)
async def archive_target(
    tenant_id: uuid.UUID, target_id: uuid.UUID, session: DBSession
) -> ApiResponse[CrawlTargetRead]:
    target = await CrawlerService(session).archive_target(tenant_id=tenant_id, target_id=target_id)
    return ApiResponse.ok(CrawlTargetRead.model_validate(target))


@router.post(
    "/targets/{target_id}/run",
    response_model=ApiResponse[CrawlJobRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequireTenantRole())],
    summary="Run crawl target",
    description="Create or reuse a manual crawl job using the supplied idempotency key.",
)
async def run_target(
    tenant_id: uuid.UUID,
    target_id: uuid.UUID,
    payload: CrawlRunCreate,
    session: DBSession,
) -> ApiResponse[CrawlJobRead]:
    job = await CrawlerService(session).create_or_reuse_job(
        tenant_id=tenant_id,
        payload=CrawlJobCreate(target_id=target_id, idempotency_key=payload.idempotency_key),
    )
    return ApiResponse.ok(CrawlJobRead.model_validate(job))


@router.get(
    "/jobs",
    response_model=ApiResponse[Page[CrawlJobRead]],
    dependencies=[Depends(RequireTenantRole())],
    summary="List crawl jobs",
    description="List and filter tenant-scoped crawl jobs.",
)
async def list_jobs(
    tenant_id: uuid.UUID,
    session: DBSession,
    pagination: Pagination,
    target_id: uuid.UUID | None = None,
    job_status: Annotated[CrawlJobStatus | None, Query(alias="status")] = None,
    handler_name: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> ApiResponse[Page[CrawlJobRead]]:
    jobs, total = await CrawlerService(session).list_jobs(
        tenant_id=tenant_id,
        limit=pagination.limit,
        offset=pagination.offset,
        target_id=target_id,
        status=job_status,
        handler_name=handler_name,
        created_from=created_from,
        created_to=created_to,
    )
    return ApiResponse.ok(
        Page(
            items=[CrawlJobRead.model_validate(job) for job in jobs],
            total=total,
            limit=pagination.limit,
            offset=pagination.offset,
        )
    )


@router.get(
    "/jobs/{job_id}",
    response_model=ApiResponse[CrawlJobRead],
    dependencies=[Depends(RequireTenantRole())],
    summary="Get crawl job",
    description="Get one tenant-scoped crawl job and its result.",
)
async def get_job(
    tenant_id: uuid.UUID, job_id: uuid.UUID, session: DBSession
) -> ApiResponse[CrawlJobRead]:
    job = await CrawlerService(session).get_job(tenant_id=tenant_id, job_id=job_id)
    return ApiResponse.ok(CrawlJobRead.model_validate(job))


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=ApiResponse[CrawlJobRead],
    dependencies=[Depends(RequireTenantRole(TenantRole.OWNER, TenantRole.ADMIN))],
    summary="Cancel crawl job",
    description="Cancel a local pending job or its active Hatchet run.",
    responses=error_responses(
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_409_CONFLICT,
        status.HTTP_503_SERVICE_UNAVAILABLE,
    ),
)
async def cancel_job(
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    session: DBSession,
    canceller: Annotated[CrawlRunCanceller | None, Depends(get_crawl_run_canceller)],
) -> ApiResponse[CrawlJobRead]:
    job = await CrawlerService(session).cancel_job(
        tenant_id=tenant_id,
        job_id=job_id,
        canceller=canceller,
    )
    return ApiResponse.ok(CrawlJobRead.model_validate(job))


@router.post(
    "/jobs/{job_id}/retry",
    response_model=ApiResponse[CrawlJobRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequireTenantRole(TenantRole.OWNER, TenantRole.ADMIN))],
    summary="Retry crawl job",
    description="Create a new job linked to a failed or cancelled job.",
)
async def retry_job(
    tenant_id: uuid.UUID, job_id: uuid.UUID, session: DBSession
) -> ApiResponse[CrawlJobRead]:
    job = await CrawlerService(session).retry_job(tenant_id=tenant_id, job_id=job_id)
    return ApiResponse.ok(CrawlJobRead.model_validate(job))


@router.get(
    "/handlers",
    response_model=ApiResponse[list[CrawlHandlerRead]],
    dependencies=[Depends(RequireTenantRole())],
    summary="List crawler handlers",
    description="List handler names available to crawl targets.",
)
async def list_handlers() -> ApiResponse[list[CrawlHandlerRead]]:
    return ApiResponse.ok([CrawlHandlerRead(name=name) for name in sorted(registry.values())])


@router.get(
    "/metrics",
    response_model=ApiResponse[CrawlMetrics],
    dependencies=[Depends(RequireTenantRole())],
    summary="Get crawler metrics",
    description="Return status counts and lifecycle duration percentiles for up to 31 days.",
)
async def get_metrics(
    tenant_id: uuid.UUID,
    session: DBSession,
    from_at: datetime | None = None,
    to_at: datetime | None = None,
) -> ApiResponse[CrawlMetrics]:
    end = _as_utc(to_at) if to_at else datetime.now(UTC)
    start = _as_utc(from_at) if from_at else end - timedelta(hours=24)
    metrics = await CrawlerService(session).metrics(tenant_id=tenant_id, from_at=start, to_at=end)
    return ApiResponse.ok(metrics)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
