"""Monthly historical snapshots; reference outcomes never enter analysis/AI packets."""

import calendar
import uuid
from dataclasses import replace
from datetime import date

from .equity_models import COMPANIES, RULE_VERSION
from .equity_pipeline import run_equity
from .equity_sources import Dataset, acquire
from .storage import atomic_write, write_json

STUDIES = {
    "pre-2025-spk": (
        date(2024, 9, 30),
        date(2025, 4, 29),
        date(2025, 4, 30),
        "2025/28 SPK tedbiri; kesinleşmiş suç etiketi değil",
    ),
    "pre-2026-funds": (
        date(2025, 5, 31),
        date(2026, 9, 16),
        date(2026, 9, 17),
        "Fonların TEFAS işlemlerinin kapatılması; şirket iflası etiketi değil",
    ),
}


def snapshot_dates(study):
    start, last, _, _ = STUDIES[study]
    dates, cursor = [], start
    while cursor <= last:
        end = cursor.replace(day=calendar.monthrange(cursor.year, cursor.month)[1])
        if end > last:
            break
        dates.append(end)
        cursor = date(end.year + (end.month == 12), end.month % 12 + 1, 1)
    if not dates or dates[-1] != last:
        dates.append(last)
    return dates


def run_replay(
    settings,
    store,
    *,
    company_id,
    study,
    bundle=None,
    refresh=False,
    progress=lambda _: None,
    dataset=None,
    codex_factory=None,
    offline=False,
):
    dates = snapshot_dates(study)
    replay_id = str(uuid.uuid4())
    directory = settings.data_dir / "replays" / replay_id
    directory.mkdir(parents=True, exist_ok=False)
    rows, cancelled = [], False
    # Acquire once to the final cutoff, then filter BOTH documents and prices for every run.
    try:
        data = (
            dataset
            if dataset is not None
            else acquire(
                settings,
                COMPANIES[company_id],
                dates[-1],
                bundle=bundle,
                refresh=refresh,
                progress=progress,
                offline=offline,
            )
        )
    except KeyboardInterrupt:
        data, cancelled = Dataset(), True
    remaining_ai_calls = 128
    for day in dates:
        if cancelled:
            break
        progress(f"Geçmiş değerlendirme {day}")
        try:
            analysis, assessment = run_equity(
                replace(settings, max_ai_calls=min(settings.max_ai_calls, remaining_ai_calls)),
                store,
                company_id=company_id,
                as_of=day,
                dataset=data,
                progress=progress,
                codex=codex_factory(day) if codex_factory else None,
            )
        except KeyboardInterrupt:
            cancelled = True
            break
        rows.append(
            {
                "as_of": day.isoformat(),
                "run_id": analysis.run_id,
                "status": assessment.status,
                "outcome": assessment.outcome,
                "coverage": assessment.coverage,
                "rule_ids": [f.rule_id for f in assessment.findings if f.level != "context"],
                "known_regulatory": any(s.kind == "regulatory" for s in analysis.sources)
                or any(f.origin == "known_regulatory" for f in assessment.findings),
                "indicator_attention": assessment.outcome == "dikkat_gerektiriyor",
                "source_count": len(analysis.sources),
                "ai_calls": analysis.ai.get("calls", 0),
            }
        )
        remaining_ai_calls -= analysis.ai.get("calls", 0)
        write_json(
            directory / "checkpoint.json",
            {"rows": rows, "remaining": [d.isoformat() for d in dates[len(rows) :]]},
        )
        if analysis.ai.get("cancelled"):
            cancelled = True
            break
    event = STUDIES[study][2]
    first = next((r["as_of"] for r in rows if r["indicator_attention"]), None)
    first_signal = next(
        (r["as_of"] for r in rows if r["outcome"] in {"sinirli_isaret", "dikkat_gerektiriyor"}),
        None,
    )
    known = next((r["as_of"] for r in rows if r["known_regulatory"]), None)
    result = {
        "schema_version": "tr-replay-1.0",
        "id": replay_id,
        "company": company_id,
        "study": study,
        "rule_version": RULE_VERSION,
        "event_date": event.isoformat(),
        "event_description": STUDIES[study][3],
        "status": "cancelled"
        if cancelled
        else "complete"
        if all(r["status"] == "complete" for r in rows)
        else "partial",
        "first_indicator_attention": first,
        "first_indicator_signal": first_signal,
        "first_known_regulatory_snapshot": known,
        "lead_days": (event - date.fromisoformat(first)).days if first else None,
        "ai_call_limit": 128,
        "ai_calls_used": 128 - remaining_ai_calls,
        "snapshots": rows,
        "remaining_dates": [d.isoformat() for d in dates[len(rows) :]],
        "limitations": [
            "İlk uyarı ay sonu taramasında gözlenen tarihtir; kesin günlük ilk sinyal tarihi değildir.",
            "Referans olaylar geçmiş sonuç açıklamasıdır; AI girdisi veya eşik ayarlama hedefi değildir.",
            "OZATD bilinen vaka olduğu için deney keşifseldir; piyasa geneli tahmin başarısı ölçülmedi.",
            "SPK tedbirinin yokluğu temiz şirket etiketi değildir. HATSN karşılaştırması da negatif gerçek etiket sayılmaz.",
        ],
    }
    write_json(directory / "replay.json", result)
    lines = [
        f"# {company_id.upper()} — {study}",
        "",
        f"Durum: {result['status']}",
        f"Göstergelerden ilk dikkat: {first or 'üretilmedi'}",
        f"Göstergelerden ilk sınırlı işaret/dikkat: {first_signal or 'üretilmedi'}",
        f"Bilinen tedbir içeren ilk değerlendirme: {known or 'veri yok'}",
        f"Referans olaya kalan gün: {result['lead_days']}",
        "",
        "| Tarih | Sonuç | Durum | Kaynak | Kurallar |",
        "|---|---|---|---:|---|",
    ]
    lines += [
        f"| {r['as_of']} | {r['outcome']} | {r['status']} | {r['source_count']} | {', '.join(r['rule_ids'])} |"
        for r in rows
    ]
    lines += ["", *[f"- {x}" for x in result["limitations"]]]
    atomic_write(directory / "replay.md", ("\n".join(lines) + "\n").encode())
    store.save_replay(result)
    return result
