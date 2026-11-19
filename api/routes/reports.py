"""M&E situation-report endpoints.

Generate a structured situation brief from multiple ReliefWeb documents (streamed
over SSE, then auto-saved), and manage the user's saved reports. Reuses the chat
retrieval/context/streaming primitives; report-specific retrieval + directive live
in rag.report_service, the LLM chain in rag.chain, persistence in rag.reports.
"""
import json
import logging
import re
from datetime import date
from uuid import uuid4

import anyio
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from analytics import technical_report
from analytics.countries import iso3_for
from analytics.indicators import indicators_for
from analytics.narrative_check import verify_narrative
from config import get_settings
from ingestion import analytics
from rag import report_images
from rag import reports as report_store
from rag.chain import build_report_chain
from rag.rag_context import _build_context_and_sources
from rag.citations import normalize_citations, normalize_table_delimiters
from rag.report_pdf import render_report_pdf
from rag.report_compare import Checked, verify_comparison
from rag.report_service import (
    COMPARISON_HEADINGS, build_comparison_block, build_report_directive, report_title,
    retrieve_for_report,
)
from api.routes.auth import get_current_user
from api.routes.chat import (
    _BUSY_MESSAGE, _GENERIC_ERROR_MESSAGE, _astream_with_retry, _is_high_demand,
)
from api.errors import ErrorCode, api_error
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

# Static fallback country list — canonical country names as indexed in the `country`
# column, so the retriever's country filter matches. Used when the `documents` table
# cannot be read (or is still empty) so the form's country dropdown is never empty.
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
    date_from: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    date_to: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    language: Literal["tr", "en"] = "en"
    report_type: Literal[
        "situation", "indicator_monitoring", "needs_assessment", "technical_monitoring"
    ] = "situation"
    # Set by "Run next period": the saved report this one continues. The new
    # report compares against it ("What changed since the last report").
    previous_report_id: Optional[str] = Field(default=None, min_length=1, max_length=64)

    @field_validator("date_from", "date_to")
    @classmethod
    def _real_date(cls, v: Optional[str]) -> Optional[str]:
        # The pattern lets "2026-02-30" through; it would crash the analysis.
        if v is not None:
            date.fromisoformat(v)
        return v

    @field_validator("theme")
    @classmethod
    def _known_theme(cls, v: Optional[str]) -> Optional[str]:
        # theme lands in the report prompt and the SQL filter: only the form's values.
        if v is not None and v not in THEMES:
            raise ValueError("unknown theme")
        return v


def _no_docs_message(req: ReportRequest) -> str:
    scope = req.theme or ("tüm sektörler" if req.language == "tr" else "all sectors")
    window = f"{req.date_from or '…'}–{req.date_to or '…'}"
    if req.language == "tr":
        return (
            f"**{req.country}** · {scope} · {window} için eşleşen belge bulunamadı.\n\n"
            "Farklı bir ülke, sektör ya da tarih aralığı deneyin."
        )
    return (
        f"No matching documents were found for **{req.country}** · {scope} · {window}.\n\n"
        "Try a different country, theme, or date range."
    )


def _no_findings_message(req: ReportRequest) -> str:
    """technical_monitoring için boş-bulgu mesajı — _no_docs_message'ın "belge bulunamadı"
    ifadesi yanlış olur, çünkü bu rapor tipi belge-retrieval değil HDX HAPI istatistik
    pipeline'ı kullanır."""
    window = f"{req.date_from or '…'}–{req.date_to or '…'}"
    if req.language == "tr":
        return (
            f"**{req.country}** için seçilen dönemde ({window}) HDX HAPI'den istatistiksel "
            "analiz yapmaya yetecek gösterge verisi bulunamadı."
        )
    return (
        f"No HDX HAPI indicator data sufficient for statistical analysis was found for "
        f"**{req.country}** in the selected period ({window})."
    )


# A technical report on a sector HDX HAPI has no series for (or none for this country):
# the interface names it by the code, in its own language.
_NO_SECTOR_DATA_MESSAGE = (
    "HDX HAPI has no quantitative series for this sector in this country, so a technical "
    "monitoring report can't be made for it. Choose \"All sectors\" or another report type."
)


def _no_sector_data_event() -> ServerSentEvent:
    return ServerSentEvent(event="error", data=json.dumps(
        {"code": ErrorCode.no_sector_data.value, "message": _NO_SECTOR_DATA_MESSAGE}))


def _no_iso3_message(req: ReportRequest) -> str:
    """technical_monitoring for a country HDX HAPI has no ISO3 code for, in the
    report's language (it used to be Turkish for every report)."""
    if req.language == "tr":
        return (f"**{req.country}** için HDX HAPI ülke kodu (ISO3) bulunamadı; teknik rapor "
                "bu ülke için oluşturulamıyor.")
    return (f"No HDX HAPI country code (ISO3) was found for **{req.country}**, so a technical "
            "report cannot be generated for this country.")


# ReliefWeb tags global reports with the country "World". They stay in the index for
# chat, but a country report on "World" makes no sense, so the form leaves it out.
_NOT_A_COUNTRY = {"World"}


def _countries() -> list[str]:
    """Country options for the form. Prefer the indexed-derived list when the scan
    cache is warm (precise, data-backed); fall back to the static COUNTRIES snapshot
    when the cache is cold — e.g. a fresh deploy on Render's ephemeral filesystem — so
    the dropdown is never empty and report generation is never blocked."""
    try:
        countries = analytics.distinct_countries() or COUNTRIES
    except Exception as exc:   # the form must never be blocked by the list query
        logger.warning("Indexed country list unavailable: %s", exc)
        countries = COUNTRIES
    return [c for c in countries if c not in _NOT_A_COUNTRY]


def _series_key(row: dict) -> tuple:
    """A series is implicit: same type + country + sector + language."""
    return (row.get("report_type") or "situation", row.get("country"),
            row.get("theme"), row.get("language"))


def _previous_in_series(user_id: str, req: ReportRequest) -> dict:
    """The report ``req`` continues. 404 when it is missing or not the user's
    (same answer, so ids of other users' reports are not probeable); 422 when it
    belongs to a different series."""
    if not report_store.is_owner(user_id, req.previous_report_id):
        raise api_error(404, ErrorCode.not_found, "Previous report not found")
    previous = report_store.get_report(req.previous_report_id)
    if previous is None:
        raise api_error(404, ErrorCode.not_found, "Previous report not found")
    if _series_key(previous) != _series_key(req.model_dump()):
        raise api_error(
            422, ErrorCode.series_mismatch,
            "The previous report has a different type, country, sector or language.",
        )
    return previous


# The waiting client shows what is being read before the first word arrives; a
# report reads up to a few dozen documents, so the list is capped (the count is not).
READING_SOURCES_SHOWN = 12


def _reading_event(docs: list, source_dicts: list) -> ServerSentEvent:
    """Sent after retrieval, before the model is called: how many documents the
    report reads and the first of them as the client lists sources (no URLs)."""
    shown = [{"title": s.get("title"), "source": s.get("source"), "date": s.get("date")}
             for s in source_dicts[:READING_SOURCES_SHOWN]]
    return ServerSentEvent(event="status", data=json.dumps(
        {"stage": "reading", "count": len(docs), "sources": shown}, ensure_ascii=False))


def _computed_event(findings: technical_report.Findings, req: ReportRequest) -> ServerSentEvent:
    """Sent after the HAPI statistics are computed, before the narrative is written:
    the indicators that have data, in analysis order and the report's language,
    and the period analysed."""
    names = [ind.name(req.language) for ind in indicators_for(req.theme)
             if ind.key in findings.indicators_covered]
    return ServerSentEvent(event="status", data=json.dumps(
        {"stage": "computed", "indicators": names,
         "date_from": findings.date_from, "date_to": findings.date_to}, ensure_ascii=False))


def _checked_event(removed: int) -> ServerSentEvent:
    """Sent after the check: how many "What changed" sentences it removed."""
    return ServerSentEvent(event="status",
                           data=json.dumps({"stage": "comparison_checked", "removed": removed}))


def _checking_event() -> ServerSentEvent:
    """Sent before the check, so the viewer can say the streamed "What changed"
    text is being checked (sentences may drop out when the saved text replaces it)."""
    return ServerSentEvent(event="status", data=json.dumps({"stage": "checking_comparison"}))


async def _checked(full: str, req: ReportRequest) -> Checked:
    """A next-period report's "What changed" section after the narrow check
    (rag.report_compare): sentences that present older or undated material as new
    are dropped. Never fails: any problem keeps the text as generated."""
    return await verify_comparison(
        full, heading=COMPARISON_HEADINGS.get(req.language, COMPARISON_HEADINGS["en"]),
        date_from=req.date_from, date_to=req.date_to, language=req.language,
    )


@router.get("/reports/options")
async def report_options(user: dict = Depends(get_current_user)):
    countries = await anyio.to_thread.run_sync(_countries)
    # technical_themes: the sectors a technical monitoring report can analyse.
    return {"countries": countries, "themes": THEMES,
            "technical_themes": [t for t in THEMES if indicators_for(t)]}


@router.post("/reports/stream")
@limiter.limit(_rate_limit)
async def report_stream(request: Request, req: ReportRequest, user: dict = Depends(get_current_user)):
    if await anyio.to_thread.run_sync(report_store.count_reports, user["id"]) >= get_settings().MAX_REPORTS_PER_USER:
        raise api_error(409, ErrorCode.report_limit,
                        "Report limit reached; delete old reports to generate a new one.")
    previous = None
    if req.previous_report_id:
        previous = await anyio.to_thread.run_sync(_previous_in_series, user["id"], req)
    previous_id = previous["id"] if previous else None

    async def event_generator():
        try:
            # technical_monitoring: HAPI+istatistik pipeline'ı — belge-retrieval yoluna
            # ASLA düşmemeli (narrate-only prompt sözleşmesi). Bu yüzden erken return.
            if req.report_type == "technical_monitoring":
                iso3 = iso3_for(req.country)
                if iso3 is None:
                    yield ServerSentEvent(
                        event="token",
                        data=json.dumps(
                            {"content": _no_iso3_message(req)}, ensure_ascii=False),
                    )
                    yield ServerSentEvent(event="done", data="{}")
                    return
                if req.theme and not indicators_for(req.theme):
                    yield _no_sector_data_event()
                    yield ServerSentEvent(event="done", data="{}")
                    return

                findings = await anyio.to_thread.run_sync(
                    technical_report.compute_findings, iso3, req.date_from, req.date_to,
                    req.language, req.theme
                )
                if not findings.sections and findings.failed:
                    # HAPI could not be reached: not a sector or country without data.
                    yield ServerSentEvent(event="error", data=json.dumps({
                        "code": ErrorCode.report_failed.value,
                        "message": "HDX HAPI could not be reached. Please try again."}))
                    yield ServerSentEvent(event="done", data="{}")
                    return
                if not findings.sections and req.theme:
                    yield _no_sector_data_event()
                    yield ServerSentEvent(event="done", data="{}")
                    return
                if not findings.sections:
                    yield ServerSentEvent(
                        event="token",
                        data=json.dumps({"content": _no_findings_message(req)}, ensure_ascii=False),
                    )
                    yield ServerSentEvent(event="done", data="{}")
                    return

                yield _computed_event(findings, req)
                context = technical_report.findings_to_context(findings)
                # The period the analysis used: a requested end in the future is capped.
                date_to = findings.date_to if req.date_to else req.date_to
                directive = build_report_directive(
                    req.country, req.theme, req.date_from, date_to,
                    len(findings.indicators_covered), req.language,
                    report_type=req.report_type,
                )
                if previous:
                    directive += build_comparison_block(
                        previous, req.language, req.report_type, req.date_from, date_to
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

                # Numbers and significance claims are checked against what the model
                # was given; unverifiable sentences never reach the saved report.
                full = verify_narrative(full, findings, f"{context}\n{directive}",
                                        req.language,
                                        label=f"{req.country} / {req.theme or 'All sectors'} / "
                                              f"{req.report_type}").content
                if previous:
                    yield _checking_event()
                    checked = await _checked(full, req)
                    full = checked.content
                    yield _checked_event(checked.removed)
                section_images = technical_report.assemble_section_images(findings)
                # The HDX HAPI series the report used, listed like a report's sources.
                try:
                    data_sources = await anyio.to_thread.run_sync(
                        technical_report.data_sources, findings, req.country)
                except Exception as exc:   # the list must never block the report
                    logger.warning("Technical report sources failed: %s", exc)
                    data_sources = []
                report_id = str(uuid4())
                title = report_title(req.country, req.theme, req.date_from, date_to,
                                     report_type=req.report_type)
                await anyio.to_thread.run_sync(
                    lambda: report_store.create_report(
                        report_id, user["id"], country=req.country, theme=req.theme,
                        date_from=req.date_from, date_to=date_to, language=req.language,
                        title=title, content=full, sources=data_sources or None,
                        doc_count=len(findings.indicators_covered),
                        report_type=req.report_type,
                        cover_image=None,
                        section_images=section_images or None,
                        previous_report_id=previous_id,
                    )
                )
                if data_sources:
                    yield ServerSentEvent(
                        event="sources",
                        data=json.dumps({"sources": data_sources}, ensure_ascii=False),
                    )
                yield ServerSentEvent(
                    event="saved",
                    data=json.dumps({"report_id": report_id, "title": title}, ensure_ascii=False),
                )
                yield ServerSentEvent(event="done", data="{}")
                return

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
            yield _reading_event(docs, source_dicts)
            directive = build_report_directive(
                req.country, req.theme, req.date_from, req.date_to, len(docs), req.language,
                report_type=req.report_type,
            )
            if previous:
                directive += build_comparison_block(
                    previous, req.language, req.report_type, req.date_from, req.date_to
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

            # Next-period reports: drop "What changed" sentences that present older or
            # undated material as new, before citations are renumbered below.
            if previous:
                yield _checking_event()
                checked = await _checked(full, req)
                full = checked.content
                yield _checked_event(checked.removed)

            # Expand grouped citations, drop uncited/invalid sources, and renumber the
            # [n] markers + sources to a contiguous 1..N so the stored content, the PDF
            # and the on-screen Sources list all stay in sync.
            clean_content, sources = normalize_citations(
                full, source_dicts, keep_uncited=req.report_type == "indicator_monitoring")
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
                    previous_report_id=previous_id,
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
            logger.exception("Report stream error: %s", e)
            if _is_high_demand(e):
                code, friendly = ErrorCode.model_busy, _BUSY_MESSAGE
            else:
                code, friendly = ErrorCode.report_failed, _GENERIC_ERROR_MESSAGE
            yield ServerSentEvent(
                event="error",
                data=json.dumps({"code": code.value, "message": friendly}, ensure_ascii=False),
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
        raise api_error(404, ErrorCode.not_found, "Report not found")
    row = await anyio.to_thread.run_sync(report_store.get_report, report_id)
    if row is None:
        raise api_error(404, ErrorCode.not_found, "Report not found")
    return _normalize_report_type(row)


@router.delete("/reports/{report_id}")
async def delete_report(report_id: str, user: dict = Depends(get_current_user)):
    if not await anyio.to_thread.run_sync(report_store.is_owner, user["id"], report_id):
        raise api_error(404, ErrorCode.not_found, "Report not found")
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
        raise api_error(404, ErrorCode.not_found, "Report not found")
    report = await anyio.to_thread.run_sync(report_store.get_report, report_id)
    if report is None:
        raise api_error(404, ErrorCode.not_found, "Report not found")
    pdf = await anyio.to_thread.run_sync(render_report_pdf, report)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_pdf_filename(report)}"'},
    )
