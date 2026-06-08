from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import text

from .db import get_session


def upsert_article(article: dict[str, Any]) -> None:
    session = get_session()
    try:
        session.execute(
            text(
                """
                insert into articles (
                    title,
                    url,
                    source,
                    published_at,
                    published_date,
                    content_text
                ) values (
                    :title,
                    :url,
                    :source,
                    :published_at,
                    :published_date,
                    :content_text
                )
                on conflict (url) do update set
                    title = excluded.title,
                    source = excluded.source,
                    published_at = excluded.published_at,
                    published_date = excluded.published_date,
                    content_text = excluded.content_text
                """
            ),
            {
                "title": article.get("title"),
                "url": article.get("url"),
                "source": article.get("source"),
                "published_at": article.get("published_at"),
                "published_date": article.get("published_date"),
                "content_text": article.get("content_text"),
            },
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def save_articles(articles: list[dict[str, Any]]) -> int:
    count = 0
    for article in articles:
        upsert_article(article)
        count += 1
    return count


def get_recent_articles(limit: int = 100) -> list[dict[str, Any]]:
    session = get_session()
    try:
        result = session.execute(
            text(
                """
                select id, title, url, source, published_at, published_date, content_text
                from articles
                order by published_at desc
                limit :limit_value
                """
            ),
            {"limit_value": int(limit)},
        )
        return [dict(row) for row in result.mappings().all()]
    finally:
        session.close()


def get_articles_by_ticker(
    ticker: str,
    start_date: date | datetime | str | None = None,
    end_date: date | datetime | str | None = None,
) -> list[dict[str, Any]]:
    session = get_session()
    try:
        clauses = ["t.ticker = :ticker"]
        params: dict[str, Any] = {"ticker": ticker.strip().upper()}
        if start_date is not None:
            clauses.append("a.published_date >= :start_date")
            params["start_date"] = str(start_date)[:10]
        if end_date is not None:
            clauses.append("a.published_date <= :end_date")
            params["end_date"] = str(end_date)[:10]

        result = session.execute(
            text(
                f"""
                select a.id, a.title, a.url, a.source, a.published_at, a.published_date, a.content_text
                from articles a
                join article_tickers t on t.article_id = a.id
                where {' and '.join(clauses)}
                order by a.published_at desc
                """
            ),
            params,
        )
        return [dict(row) for row in result.mappings().all()]
    finally:
        session.close()
