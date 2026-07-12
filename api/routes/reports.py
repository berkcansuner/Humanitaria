"""M&E situation-report endpoints.

Generate a structured situation brief from multiple ReliefWeb documents (streamed
over SSE, then auto-saved), and manage the user's saved reports. Reuses the chat
retrieval/context/streaming primitives; report-specific retrieval + directive live
in rag.report_service, the LLM chain in rag.chain, persistence in rag.reports.
"""
import json
import logging
import re
from uuid import uuid4

import anyio
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Literal, Optional
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from config import get_settings
from ingestion import analytics
from rag import report_images
from rag import reports as report_store
from rag.chain import build_report_chain
from rag.rag_context import _build_context_and_sources
from rag.citations import normalize_citations, normalize_table_delimiters
from rag.report_pdf import render_report_pdf
from rag.report_service import (
    build_report_directive, report_title, retrieve_for_report,
)
from api.routes.auth import get_current_user
from api.routes.chat import (
    _BUSY_MESSAGE, _GENERIC_ERROR_MESSAGE, _astream_with_retry, _is_high_demand,
)
from api.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


def _rate_limit() -> str:
    return get_settings().RATE_LIMIT


def settings_images_enabled() -> bool:
    return get_settings().REPORT_IMAGES_ENABLED


# ReliefWeb 'theme' facet (canonical theme.name strings — must match the indexed
# metadata for the $or(theme/themes) filter to hit). Stable, small, curated list.
THEMES = [
    "Agriculture",
    "Camp Coordination and Camp Management",
    "Climate Change and Environment",
    "Contributions",
    "Coordination",
    "Disaster Management",
    "Education",
    "Food and Nutrition",
    "Gender",
    "Health",
    "HIV/Aids",
    "Humanitarian Financing",
    "Logistics and Telecommunications",
    "Mine Action",
    "Peacekeeping and Peacebuilding",
    "Protection and Human Rights",
    "Recovery and Reconstruction",
    "Safety and Security",
    "Shelter and Non-Food Items",
    "Water Sanitation Hygiene",
]

# Static fallback country list — the canonical country names as they appear in the
# Pinecone metadata (snapshot of the indexed `country` values), so the $eq/$in filter
# matches. Used when the scan cache is cold (e.g. a fresh deploy on Render's ephemeral
# filesystem wipes .reports_cache.json) so the form's country dropdown is never empty.
COUNTRIES = [
    "Afghanistan", "Albania", "Algeria", "Angola", "Antigua and Barbuda", "Argentina",
    "Armenia", "Azerbaijan", "Bahamas", "Bangladesh", "Barbados", "Belarus", "Belgium",
    "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil",
    "Brunei Darussalam", "Bulgaria", "Burkina Faso", "Burundi", "Cambodia", "Cameroon",
    "Central African Republic", "Chad", "Chile", "China", "China - Taiwan Province",
    "Colombia", "Comoros", "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czechia",
    "Côte d'Ivoire", "Democratic People's Republic of Korea",
    "Democratic Republic of the Congo", "Djibouti", "Dominican Republic", "Ecuador",
    "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Ethiopia", "Fiji",
    "Gabon", "Gambia", "Georgia", "Ghana", "Greece", "Guam", "Guatemala", "Guinea",
    "Guinea-Bissau", "Guyana", "Haiti", "Honduras", "Hungary", "India", "Indonesia", "Iran",
    "Iraq", "Ireland", "Israel", "Italy", "Jamaica", "Japan", "Jordan", "Kazakhstan",
    "Kenya", "Kyrgyzstan", "Lao People's Democratic Republic", "Latvia", "Lebanon",
    "Lesotho", "Libya", "Lithuania", "Madagascar", "Malawi", "Malaysia", "Mali",
    "Mauritania", "Mexico", "Micronesia", "Moldova", "Mongolia", "Montenegro", "Morocco",
    "Mozambique", "Myanmar", "Namibia", "Nepal", "Niger", "Nigeria", "Norway", "Oman",
    "Pakistan", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland",
    "Republic of Korea", "Romania", "Russian Federation", "Rwanda",
    "Saint Vincent and the Grenadines", "Sao Tome and Principe", "Saudi Arabia", "Senegal",
    "Serbia", "Sierra Leone", "Slovakia", "Solomon Islands", "Somalia", "South Africa",
    "South Sudan", "Sri Lanka", "Sudan", "Suriname", "Syrian Arab Republic", "Tajikistan",
    "Thailand", "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Türkiye", "Uganda",
    "Ukraine", "United Republic of Tanzania", "United States of America", "Uruguay",
    "Uzbekistan", "Vanuatu", "Venezuela", "Viet Nam", "World", "Yemen", "Zambia", "Zimbabwe",
    "occupied Palestinian territory", "the Republic of North Macedonia",
]


class ReportRequest(BaseModel):
    country: str = Field(..., min_length=1, max_length=120)
    theme: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    language: Literal["tr", "en"] = "en"
    report_type: Literal["situation", "indicator_monitoring", "needs_assessment", "technical_monitoring"] = "situation"


def _no_docs_message(req: ReportRequest) -> str:
    scope = req.theme or ("tüm sektörler" if req.language == "tr" else "all sectors")
    window = f"{req.date_from or '…'}–{req.date_to or '…'}"
    if req.language == "tr":
        return (
            f"**{req.country}** · {scope} · {window} için eşleşen belge bulunamadı.\n\n"
            "Farklı bir ülke, tema veya tarih aralığı deneyin."
        )
    return (
        f"No matching documents were found for **{req.country}** · {scope} · {window}.\n\n"
        "Try a different country, theme, or date range."
    )


def _countries() -> list[str]:
    """Country options for the form. Prefer the indexed-derived list when the scan
    cache is warm (precise, data-backed); fall back to the static COUNTRIES snapshot
    when the cache is cold — e.g. a fresh deploy on Render's ephemeral filesystem — so
    the dropdown is never empty and report generation is never blocked."""
    return analytics.distinct_countries() or COUNTRIES


@router.get("/reports/options")
async def report_options(user: dict = Depends(get_current_user)):
    countries = await anyio.to_thread.run_sync(_countries)
    return {"countries": countries, "themes": THEMES}


@router.post("/reports/stream")
@limiter.limit(_rate_limit)
async def report_stream(request: Request, req: ReportRequest, user: dict = Depends(get_current_user)):
    async def event_generator():
        try:
            docs = await retrieve_for_report(
                req.country, req.theme, req.date_from, req.date_to, report_type=req.report_type
            )
            if not docs:
                yield ServerSentEvent(
                    event="token",
                    data=json.dumps({"content": _no_docs_message(req)}, ensure_ascii=False),
                )
                yield ServerSentEvent(event="done", data="{}")
                return

            context, source_dicts = _build_context_and_sources(docs)
            directive = build_report_directive(
                req.country, req.theme, req.date_from, req.date_to, len(docs), req.language,
                report_type=req.report_type,
            )
            chain = build_report_chain(req.report_type)

            full = ""
            async for chunk in _astream_with_retry(
                chain, {"question": directive, "context": context},
                get_settings().CHAT_LLM_MAX_RETRIES,
            ):
                if chunk:
                    full += chunk
                    yield ServerSentEvent(
                        event="token",
                        data=json.dumps({"content": chunk}, ensure_ascii=False),
                    )

            # Expand grouped citations, drop uncited/invalid sources, and renumber the
            # [n] markers + sources to a contiguous 1..N so the stored content, the PDF
            # and the on-screen Sources list all stay in sync.
            clean_content, sources = normalize_citations(full, source_dicts)
            # Repair over-padded Markdown table delimiter rows (indicator reports) so the
            # web renderer parses the table instead of showing a <br>-joined paragraph.
            clean_content = normalize_table_delimiters(clean_content)

            cover_image = None
            section_images = []
            if settings_images_enabled():
                try:
                    yield ServerSentEvent(
                        event="images_status",
                        data=json.dumps({"stage": "cover"}, ensure_ascii=False),
                    )
                    cover_image = await anyio.to_thread.run_sync(
                        report_images.generate_image,
                        report_images.build_cover_prompt(req.country, req.theme, req.report_type),
                    )
                    headings = report_images.extract_section_headings(clean_content)
                    for h in headings:
                        yield ServerSentEvent(
                            event="images_status",
                            data=json.dumps({"stage": "section", "heading": h}, ensure_ascii=False),
                        )
                        img = await anyio.to_thread.run_sync(
                            report_images.generate_image,
                            report_images.build_section_prompt(req.country, req.theme, h),
                        )
                        if img:
                            section_images.append({"heading": h, "image": img})
                    yield ServerSentEvent(
                        event="images",
                        data=json.dumps({"cover": cover_image, "sections": section_images},
                                        ensure_ascii=False),
                    )
                except Exception as exc:  # image generation must never block the report
                    logger.warning("Report image block failed, saving text-only: %s", exc)
                    cover_image, section_images = None, []

            # Auto-save only after a full stream (an aborted report is never written).
            report_id = str(uuid4())
            title = report_title(req.country, req.theme, req.date_from, req.date_to,
                                 report_type=req.report_type)
            await anyio.to_thread.run_sync(
                lambda: report_store.create_report(
                    report_id, user["id"], country=req.country, theme=req.theme,
                    date_from=req.date_from, date_to=req.date_to, language=req.language,
                    title=title, content=clean_content, sources=sources, doc_count=len(docs),
                    report_type=req.report_type,
                    cover_image=cover_image,
                    section_images=section_images or None,
                )
            )

            if sources:
                yield ServerSentEvent(
                    event="sources",
                    data=json.dumps({"sources": sources}, ensure_ascii=False),
                )
            yield ServerSentEvent(
                event="saved",
                data=json.dumps({"report_id": report_id, "title": title}, ensure_ascii=False),
            )
            yield ServerSentEvent(event="done", data="{}")

        except Exception as e:
            logger.error("Report stream error: %s", e)
            friendly = _BUSY_MESSAGE if _is_high_demand(e) else _GENERIC_ERROR_MESSAGE
            yield ServerSentEvent(
                event="error",
                data=json.dumps({"message": friendly}, ensure_ascii=False),
            )
            yield ServerSentEvent(event="done", data="{}")

    return EventSourceResponse(event_generator())


def _normalize_report_type(row: dict) -> dict:
    """Pre-migration rows carry NULL report_type in the DB; the API always
    returns a concrete type so the frontend never has to special-case null."""
    row = dict(row)
    row["report_type"] = row.get("report_type") or "situation"
    return row


# NB: the bare "/reports" path is the SPA client route (served by the catch-all in
# api/main.py). Keeping the list under "/reports/list" avoids the API shadowing the
# page — mirrors the admin split (client "/admin/ingestion" vs API "/admin/ingest/*").
@router.get("/reports/list")
async def list_reports(user: dict = Depends(get_current_user)):
    rows = await anyio.to_thread.run_sync(report_store.list_reports, user["id"])
    return {"reports": [_normalize_report_type(r) for r in rows]}


@router.get("/reports/{report_id}")
async def get_report(report_id: str, user: dict = Depends(get_current_user)):
    if not await anyio.to_thread.run_sync(report_store.is_owner, user["id"], report_id):
        raise HTTPException(status_code=404, detail="Report not found")
    row = await anyio.to_thread.run_sync(report_store.get_report, report_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return _normalize_report_type(row)


@router.delete("/reports/{report_id}")
async def delete_report(report_id: str, user: dict = Depends(get_current_user)):
    if not await anyio.to_thread.run_sync(report_store.is_owner, user["id"], report_id):
        raise HTTPException(status_code=404, detail="Report not found")
    await anyio.to_thread.run_sync(report_store.delete_report, report_id)
    return {"ok": True}


def _pdf_filename(report: dict) -> str:
    parts = [report.get("country") or "report", report.get("date_from"), report.get("date_to")]
    base = "_".join(str(p) for p in parts if p)
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", base).strip("_") or "report"
    return f"Humanitaria_{safe}.pdf"


@router.get("/reports/{report_id}/pdf")
@limiter.limit(_rate_limit)
async def report_pdf(request: Request, report_id: str, user: dict = Depends(get_current_user)):
    if not await anyio.to_thread.run_sync(report_store.is_owner, user["id"], report_id):
        raise HTTPException(status_code=404, detail="Report not found")
    report = await anyio.to_thread.run_sync(report_store.get_report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    pdf = await anyio.to_thread.run_sync(render_report_pdf, report)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_pdf_filename(report)}"'},
    )
