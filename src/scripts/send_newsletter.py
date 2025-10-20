"""Send the generated briefing through Buttondown."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Optional

from src.integrations.buttondown import ButtondownClient, ButtondownError

DEFAULT_SUBJECT = "USD/COP - Briefing 2 minutos"
DEFAULT_NEWSLETTER_SLUG = "juandavidsanchezlatorre"
DEFAULT_TAGS = ["usd-cop", "briefing"]


def resolve_date(value: str) -> dt.date:
    if value == "today":
        return dt.date.today()
    return dt.date.fromisoformat(value)


def discover_preheader(markdown_body: str) -> str:
    """Pick the first relevant line to use as preheader text."""
    for line in markdown_body.splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        return text
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Send the USD/COP briefing via Buttondown.")
    parser.add_argument("--date", default="today", help="Date in YYYY-MM-DD format or 'today'")
    parser.add_argument(
        "--briefing-dir",
        default="reports/briefings",
        help="Directory where briefing markdown files are stored",
    )
    parser.add_argument(
        "--subject",
        default=None,
        help="Override the email subject. Defaults to a templated subject including the date.",
    )
    parser.add_argument(
        "--newsletter",
        default=None,
        help="Optional newsletter slug override. Defaults to env or project default.",
    )
    parser.add_argument(
        "--draft-only",
        action="store_true",
        help="Create the draft but do not queue it for delivery.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the payload without calling the Buttondown API.",
    )
    args = parser.parse_args()

    report_date = resolve_date(args.date)
    date_str = report_date.strftime("%Y-%m-%d")

    briefing_path = Path(args.briefing_dir) / f"briefing_{date_str}.md"
    if not briefing_path.exists():
        raise SystemExit(f"Briefing not found: {briefing_path}")

    markdown_body = briefing_path.read_text(encoding="utf-8")
    preheader = discover_preheader(markdown_body)

    subject = args.subject or f"{DEFAULT_SUBJECT} | {date_str}"
    run_suffix = os.getenv("GITHUB_RUN_ID") or os.getenv("GITHUB_RUN_NUMBER")
    if run_suffix:
        slug = f"usd-cop-briefing-{date_str}-{run_suffix}"
    else:
        slug = f"usd-cop-briefing-{date_str}-{dt.datetime.utcnow():%H%M%S}"

    newsletter_slug = (
        args.newsletter
        or os.getenv("BUTTONDOWN_NEWSLETTER")
        or DEFAULT_NEWSLETTER_SLUG
    )
    api_key = os.getenv("BUTTONDOWN_API_KEY")
    base_url = os.getenv("BUTTONDOWN_API_BASE")

    payload_preview = {
        "newsletter": newsletter_slug,
        "subject": subject,
        "slug": slug,
        "preheader": preheader,
        "tags": DEFAULT_TAGS,
    }

    if args.dry_run:
        print("DRY RUN -- would send newsletter with payload:")
        print(json.dumps(payload_preview, ensure_ascii=False, indent=2))
        return

    if not api_key:
        raise SystemExit("BUTTONDOWN_API_KEY environment variable is required.")

    try:
        client = ButtondownClient(api_key=api_key, base_url=base_url)
        email = client.create_email(
            subject=subject,
            body=markdown_body,
            preheader=preheader or None,
            newsletter=newsletter_slug,
            slug=slug,
            tags=DEFAULT_TAGS,
        )

        email_id: Optional[str] = email.get("id")  # type: ignore[assignment]
        if not email_id:
            raise ButtondownError("Buttondown did not return an email identifier.")

        print(f"Draft created in Buttondown (id={email_id}).")

        if args.draft_only:
            return

        queued = client.queue_email(email_id)
        print(
            f"Newsletter queued for delivery (status={queued.get('status', 'unknown')})."
        )
    except ButtondownError as exc:
        raise SystemExit(f"Buttondown API error: {exc}") from exc


if __name__ == "__main__":
    main()
