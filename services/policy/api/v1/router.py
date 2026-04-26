"""HTTP routes for the policy API v1."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from shared.domain import PolicyStatus
from shared.domain.policy_state import InvalidPolicyTransitionError

from services.policy.api.dependencies import PolicyServiceDep
from services.policy.schemas import (
    BindPolicyRequest,
    CreateEndorsementRequest,
    EndorsementResponse,
    PolicyListResponse,
    PolicyResponse,
    PolicySummaryResponse,
    PolicyTransitionRequest,
)
from services.policy.services import (
    EndorsementNotFoundError,
    PolicyAlreadyBoundError,
    PolicyNotFoundError,
    QuoteNotFoundError,
)
from services.pricing.services.exceptions import QuoteExpiredError

router = APIRouter(prefix="/v1/policies", tags=["policies"])


@router.post(
    "/bind",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bind a quote into an active policy",
)
async def bind_policy(
    request: BindPolicyRequest,
    service: PolicyServiceDep,
) -> PolicyResponse:
    """Bind a quote, creating a new active policy."""
    try:
        policy = await service.bind(request)
    except QuoteNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except QuoteExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except PolicyAlreadyBoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return PolicyResponse.from_domain(
        policy,
        valid_next_states=service.valid_next_states_for(policy),
    )


@router.get(
    "/by-quote/{quote_id}",
    response_model=PolicyResponse | None,
    summary="Get the policy bound from a specific quote, if any",
)
async def get_policy_by_quote(
    quote_id: UUID,
    service: PolicyServiceDep,
) -> PolicyResponse | None:
    """Return the policy that was bound from a given quote, or null if none exists."""
    policy = await service.get_by_quote_id(quote_id)
    if policy is None:
        return None
    endorsements = await service.list_endorsements_for_policy(policy.id)
    return PolicyResponse.from_domain(
        policy,
        valid_next_states=service.valid_next_states_for(policy),
        endorsements=endorsements,
    )


@router.get(
    "/{policy_id}",
    response_model=PolicyResponse,
    summary="Get a policy by id",
)
async def get_policy(
    policy_id: UUID,
    service: PolicyServiceDep,
) -> PolicyResponse:
    """Return the full details of a policy with its endorsements."""
    try:
        policy = await service.get(policy_id)
    except PolicyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    endorsements = await service.list_endorsements_for_policy(policy_id)

    return PolicyResponse.from_domain(
        policy,
        valid_next_states=service.valid_next_states_for(policy),
        endorsements=endorsements,
    )


@router.post(
    "/{policy_id}/transition",
    response_model=PolicyResponse,
    summary="Transition a policy to a new status",
)
async def transition_policy(
    policy_id: UUID,
    request: PolicyTransitionRequest,
    service: PolicyServiceDep,
) -> PolicyResponse:
    """Move a policy to a new status (e.g. cancel, lapse, renew)."""
    try:
        policy = await service.transition(policy_id, request.new_status, request.reason)
    except PolicyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidPolicyTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return PolicyResponse.from_domain(
        policy, valid_next_states=service.valid_next_states_for(policy)
    )


@router.post(
    "/{policy_id}/endorsements",
    response_model=EndorsementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an endorsement on a policy",
)
async def create_endorsement(
    policy_id: UUID,
    request: CreateEndorsementRequest,
    service: PolicyServiceDep,
) -> EndorsementResponse:
    """Propose an endorsement (modification) to an active policy."""
    try:
        endorsement = await service.create_endorsement(policy_id, request)
    except PolicyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidPolicyTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return EndorsementResponse.from_domain(endorsement)


@router.get(
    "/{policy_id}/endorsements",
    response_model=list[EndorsementResponse],
    summary="List endorsements on a policy",
)
async def list_endorsements(
    policy_id: UUID,
    service: PolicyServiceDep,
) -> list[EndorsementResponse]:
    """Return all endorsements for the given policy."""
    try:
        await service.get(policy_id)
    except PolicyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    endorsements = await service.list_endorsements_for_policy(policy_id)
    return [EndorsementResponse.from_domain(e) for e in endorsements]


@router.post(
    "/endorsements/{endorsement_id}/approve",
    response_model=EndorsementResponse,
    summary="Approve a proposed endorsement",
)
async def approve_endorsement(
    endorsement_id: UUID,
    service: PolicyServiceDep,
) -> EndorsementResponse:
    """Approve an endorsement, moving it from proposed to approved."""
    try:
        endorsement = await service.approve_endorsement(endorsement_id)
    except EndorsementNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return EndorsementResponse.from_domain(endorsement)


@router.post(
    "/endorsements/{endorsement_id}/apply",
    response_model=EndorsementResponse,
    summary="Apply an approved endorsement",
)
async def apply_endorsement(
    endorsement_id: UUID,
    service: PolicyServiceDep,
) -> EndorsementResponse:
    """Apply an approved endorsement, marking it as in effect."""
    try:
        endorsement = await service.apply_endorsement(endorsement_id)
    except EndorsementNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return EndorsementResponse.from_domain(endorsement)


@router.get(
    "",
    response_model=PolicyListResponse,
    summary="List policies with pagination and optional status filter",
)
async def list_policies(
    service: PolicyServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    policy_status: Annotated[PolicyStatus | None, Query(alias="status")] = None,
) -> PolicyListResponse:
    """Return a paginated list of policies."""
    policies, total = await service.list_paginated(limit=limit, offset=offset, status=policy_status)
    items = [
        PolicySummaryResponse(
            id=policy.id,
            policy_number=policy.policy_number,
            insured_name=policy.insured_name,
            status=policy.status,
            period_start=policy.period.start,
            period_end=policy.period.end,
            premium=policy.premium,
        )
        for policy in policies
    ]
    return PolicyListResponse(items=items, total=total, limit=limit, offset=offset)
