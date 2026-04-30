"""Seed the database with the current HH vacancies, salaries, and tags snapshot.

Run through Docker:
    docker compose run --rm app uv run python scripts/seed_market_snapshot.py

Checks:
    docker compose run --rm app uv run python scripts/seed_market_snapshot.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import async_session_maker, create_tables
from app.models import Tag, Vacancy


DEFAULT_SNAPSHOT_PATH = Path(__file__).with_name("data") / "market_snapshot.json"


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def load_snapshot(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        snapshot = json.load(file)

    vacancies = snapshot.get("vacancies")
    if not isinstance(vacancies, list):
        raise ValueError(f"Snapshot {path} must contain a vacancies list")
    return snapshot


async def get_or_create_tag(name: str) -> Tag:
    async with async_session_maker() as session:
        result = await session.execute(select(Tag).where(Tag.name == name))
        tag = result.scalar_one_or_none()
        if tag is None:
            tag = Tag(name=name)
            session.add(tag)
            await session.commit()
            await session.refresh(tag)
        return tag


async def seed_vacancy(raw: dict[str, Any]) -> tuple[bool, int]:
    tag_names = sorted(
        {str(name).strip() for name in raw.get("tags", []) if str(name).strip()}
    )

    async with async_session_maker() as session:
        result = await session.execute(
            select(Vacancy)
            .options(selectinload(Vacancy.tags))
            .where(Vacancy.hh_id == str(raw["hh_id"]))
        )
        vacancy = result.scalar_one_or_none()
        created = vacancy is None

        if vacancy is None:
            vacancy = Vacancy(hh_id=str(raw["hh_id"]))
            session.add(vacancy)

        vacancy.url = raw["url"]
        vacancy.title = raw["title"]
        vacancy.salary_from = raw.get("salary_from")
        vacancy.salary_to = raw.get("salary_to")
        vacancy.salary_currency = raw.get("salary_currency")
        vacancy.experience = raw.get("experience")
        vacancy.search_query = raw.get("search_query") or "snapshot"
        vacancy.created_at = parse_datetime(raw.get("created_at")) or datetime.utcnow()

        tags: list[Tag] = []
        for tag_name in tag_names:
            result = await session.execute(select(Tag).where(Tag.name == tag_name))
            tag = result.scalar_one_or_none()
            if tag is None:
                tag = Tag(name=tag_name)
                session.add(tag)
                await session.flush()
            tags.append(tag)

        vacancy.tags = tags
        await session.commit()
        return created, len(tags)


async def seed_snapshot(path: Path, dry_run: bool) -> None:
    snapshot = load_snapshot(path)
    vacancies: list[dict[str, Any]] = snapshot["vacancies"]
    unique_tags = sorted(
        {
            str(tag).strip()
            for vacancy in vacancies
            for tag in vacancy.get("tags", [])
            if str(tag).strip()
        }
    )
    salaries = sum(
        1
        for vacancy in vacancies
        if vacancy.get("salary_from") is not None
        or vacancy.get("salary_to") is not None
    )

    print(
        f"Snapshot: vacancies={len(vacancies)}, tags={len(unique_tags)}, "
        f"vacancies_with_salary={salaries}"
    )

    if dry_run:
        for vacancy in vacancies[:10]:
            salary = f"{vacancy.get('salary_from') or '-'}..{vacancy.get('salary_to') or '-'}"
            print(
                f"- {vacancy['hh_id']} | {salary} {vacancy.get('salary_currency') or ''} | {vacancy['title']}"
            )
        if len(vacancies) > 10:
            print(f"... and {len(vacancies) - 10} more")
        return

    await create_tables()

    created_count = 0
    updated_count = 0
    tag_link_count = 0
    for vacancy in vacancies:
        created, tags_count = await seed_vacancy(vacancy)
        created_count += int(created)
        updated_count += int(not created)
        tag_link_count += tags_count

    print(
        f"Done: created={created_count}, updated={updated_count}, "
        f"tag_links={tag_link_count}"
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed HH market data snapshot.")
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT_PATH,
        help="Path to market_snapshot.json.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print summary without writing to DB."
    )
    args = parser.parse_args()

    await seed_snapshot(args.snapshot, args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
