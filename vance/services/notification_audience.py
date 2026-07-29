"""
Audience filtering for notifications.

Resolves a parameterized `Audience` spec into a concrete list of user_ids.
Callers compose filters declaratively; the resolver translates them into
a SQL query against users / user_profiles / candidates / placements /
fcm_tokens / employer_profiles.

All filters AND together. `user_ids`, when set, short-circuits the rest
(you're naming people explicitly).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.sql_models import (
    Candidate,
    EmployerProfile,
    FcmToken,
    Placement,
    User,
    UserProfile,
)

Role = Literal["worker", "employer", "any"]


@dataclass
class Audience:
    user_ids: Optional[list[str]] = None
    role: Role = "any"
    regions: Optional[list[str]] = None
    preferred_roles: Optional[list[str]] = None
    employment_status: Optional[list[str]] = None
    onboarding_complete: Optional[bool] = None
    joined_after: Optional[float] = None
    joined_before: Optional[float] = None
    employer_phones: Optional[list[str]] = None
    placement_status: Optional[list[str]] = None
    has_active_token: bool = True

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


def _normalize_phone(p: str) -> str:
    p = (p or "").lstrip("+").replace(" ", "").replace("-", "")
    if len(p) == 10:
        p = "91" + p
    return p


def _role_candidates_any(role_list: list[str], candidate_rows: list[Candidate]) -> set[str]:
    wanted = {r.lower() for r in role_list}
    matched = set()
    for c in candidate_rows:
        prev = []
        try:
            prev = json.loads(c.previous_roles or "[]")
        except (json.JSONDecodeError, TypeError):
            prev = []
        if any(str(r).lower() in wanted for r in prev):
            matched.add(c.phone)
    return matched


def _worker_user_ids(db: Session, aud: Audience) -> list[str]:
    """
    Worker audience resolution. Workers are keyed by phone in Candidate /
    UserProfile / Placement / fcm_tokens.phone; user_id === phone for workers
    in this codebase (Firebase UID is the phone-derived uid). We return phone
    strings as user_ids here — matches how notifications.user_id is populated
    elsewhere.
    """
    phones: Optional[set[str]] = None

    if aud.regions:
        cand_q = db.query(Candidate.phone).filter(
            or_(*[Candidate.area.ilike(f"%{r}%") for r in aud.regions])
        )
        user_q = db.query(User.phone).filter(
            or_(*[User.location.ilike(f"%{r}%") for r in aud.regions])
        )
        phones = {p[0] for p in cand_q.all()} | {p[0] for p in user_q.all()}

    if aud.employment_status:
        q = db.query(Candidate.phone).filter(Candidate.status.in_(aud.employment_status))
        rows = {p[0] for p in q.all()}
        phones = rows if phones is None else phones & rows

    if aud.onboarding_complete is not None:
        q = db.query(Candidate.phone)
        if aud.onboarding_complete:
            q = q.filter(Candidate.profile_completeness_score >= 80)
        else:
            q = q.filter(Candidate.profile_completeness_score < 80)
        rows = {p[0] for p in q.all()}
        phones = rows if phones is None else phones & rows

    if aud.joined_after is not None:
        q = db.query(Candidate.phone).filter(Candidate.created_at >= aud.joined_after)
        rows = {p[0] for p in q.all()}
        phones = rows if phones is None else phones & rows

    if aud.joined_before is not None:
        q = db.query(Candidate.phone).filter(Candidate.created_at <= aud.joined_before)
        rows = {p[0] for p in q.all()}
        phones = rows if phones is None else phones & rows

    if aud.preferred_roles:
        all_candidates = db.query(Candidate).all()
        role_match = _role_candidates_any(aud.preferred_roles, all_candidates)
        prof_q = db.query(UserProfile.phone).filter(
            or_(*[UserProfile.role.ilike(f"%{r}%") for r in aud.preferred_roles])
        )
        role_match |= {p[0] for p in prof_q.all()}
        user_q = db.query(User.phone).filter(
            or_(*[User.job_role.ilike(f"%{r}%") for r in aud.preferred_roles]
                + [User.previous_role.ilike(f"%{r}%") for r in aud.preferred_roles])
        )
        role_match |= {p[0] for p in user_q.all()}
        phones = role_match if phones is None else phones & role_match

    if aud.employer_phones or aud.placement_status:
        q = db.query(Placement.user_id)
        if aud.employer_phones:
            normalized = [_normalize_phone(p) for p in aud.employer_phones]
            q = q.filter(Placement.employer_phone.in_(normalized))
        if aud.placement_status:
            q = q.filter(Placement.status.in_(aud.placement_status))
        rows = {p[0] for p in q.all()}
        phones = rows if phones is None else phones & rows

    if phones is None:
        phones = {p[0] for p in db.query(User.phone).all()} | {
            p[0] for p in db.query(Candidate.phone).all()
        }

    return sorted(phones)


def _employer_user_ids(db: Session, aud: Audience) -> list[str]:
    phones: Optional[set[str]] = None

    if aud.regions:
        q = db.query(EmployerProfile.phone).filter(
            or_(*[EmployerProfile.location.ilike(f"%{r}%") for r in aud.regions])
        )
        phones = {p[0] for p in q.all()}

    if aud.joined_after is not None:
        q = db.query(EmployerProfile.phone).filter(EmployerProfile.created_at >= aud.joined_after)
        rows = {p[0] for p in q.all()}
        phones = rows if phones is None else phones & rows

    if aud.joined_before is not None:
        q = db.query(EmployerProfile.phone).filter(EmployerProfile.created_at <= aud.joined_before)
        rows = {p[0] for p in q.all()}
        phones = rows if phones is None else phones & rows

    if aud.employer_phones:
        normalized = {_normalize_phone(p) for p in aud.employer_phones}
        phones = normalized if phones is None else phones & normalized

    if phones is None:
        phones = {p[0] for p in db.query(EmployerProfile.phone).all()}

    return sorted(phones)


def _filter_by_active_token(db: Session, user_ids: list[str]) -> list[str]:
    if not user_ids:
        return []
    rows = (
        db.query(FcmToken.user_id)
        .filter(FcmToken.user_id.in_(user_ids), FcmToken.disabled_at.is_(None))
        .distinct()
        .all()
    )
    return sorted({r[0] for r in rows})


def resolve(db: Session, audience: Audience) -> list[str]:
    """
    Resolve an Audience to a concrete list of user_ids.

    Explicit user_ids short-circuit all other filters (except has_active_token,
    which still applies if set).
    """
    if audience.user_ids:
        result = list(dict.fromkeys(audience.user_ids))
    else:
        if audience.role == "worker":
            result = _worker_user_ids(db, audience)
        elif audience.role == "employer":
            result = _employer_user_ids(db, audience)
        else:
            w = _worker_user_ids(db, audience)
            e = _employer_user_ids(db, audience)
            result = sorted(set(w) | set(e))

    if audience.has_active_token:
        result = _filter_by_active_token(db, result)

    return result
