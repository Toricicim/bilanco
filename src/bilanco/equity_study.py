"""Offline, post-analysis evaluation. Outcome labels never enter acquisition or AI."""

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .equity_models import EquityAnalysis, EquityAssessment, cutoff
from .models import Model
from .storage import digest


class StudyCase(Model):
    company_id: str
    split: Literal["development", "test"]
    analysis: str
    assessment: str
    target_event_observed: bool
    event_date: date | None
    followup_end: date
    label_source: str = Field(min_length=12)

    @model_validator(mode="after")
    def coherent(self):
        if self.target_event_observed != (self.event_date is not None):
            raise ValueError("Olay etiketi ile olay tarihi uyuşmuyor.")
        return self


class Study(Model):
    schema_version: Literal["1.0"] = "1.0"
    target_definition: str = Field(min_length=20)
    horizon_days: int = Field(ge=1, le=3653)
    rule_version: str
    development_company_ids: list[str]
    cases: list[StudyCase] = Field(min_length=1, max_length=1000)


def _read(root, name):
    path = (root / name).resolve()
    if (
        not path.is_relative_to(root.resolve())
        or not path.is_file()
        or path.stat().st_size > 50_000_000
    ):
        raise ValueError("Çalışma dosyası bulunamadı, paket dışında veya boyut sınırını aşıyor.")
    return json.loads(path.read_text())


def evaluate_study(manifest: Path):
    if manifest.stat().st_size > 2_000_000:
        raise ValueError("Çalışma manifesti boyut sınırını aşıyor.")
    study = Study.model_validate_json(manifest.read_text())
    rows, seen = [], set()
    for case in study.cases:
        if case.company_id in seen:
            raise ValueError(
                "Bir şirket birden çok gözlemle başarı oranını şişiremez; ayrı protokol kullanın."
            )
        seen.add(case.company_id)
        if case.split == "test" and case.company_id in study.development_company_ids:
            raise ValueError("Geliştirmede görülen şirket bağımsız test şirketi olamaz.")
        raw = _read(manifest.parent, case.analysis)
        analysis = EquityAnalysis.model_validate(raw)
        assessment = EquityAssessment.model_validate(_read(manifest.parent, case.assessment))
        sha = digest(json.dumps(raw, sort_keys=True, ensure_ascii=False).encode())
        if assessment.source_analysis_sha256 != sha or assessment.source_run_id != analysis.run_id:
            raise ValueError("Analiz/değerlendirme kaydı hash veya koşu kimliğiyle eşleşmiyor.")
        if not (
            case.company_id == analysis.company_id
            and assessment.company == analysis.company
            and assessment.as_of == analysis.as_of
        ):
            raise ValueError("Şirket veya bilgi kesimi eşleşmiyor.")
        if (
            analysis.rule_version != study.rule_version
            or assessment.rule_version != study.rule_version
        ):
            raise ValueError("Farklı kural sürümlerinin başarıları aynı deneyde birleştirilemez.")
        if any(s.available_at > cutoff(analysis.as_of) for s in analysis.sources) or any(
            b.day > analysis.as_of for series in analysis.market for b in series.bars
        ):
            raise ValueError("Kaynak veya piyasa kaydında tarih sızıntısı var.")
        end = analysis.as_of + timedelta(days=study.horizon_days)
        if case.followup_end < end:
            raise ValueError(
                "Takip penceresi tamamlanmamış; olay görülmeyen şirket kontrol sayılamaz."
            )
        if case.event_date and not analysis.as_of < case.event_date <= end:
            raise ValueError("Olay analizden sonra ve tanımlı takip penceresinde olmalı.")
        if assessment.investor_review is None:
            raise ValueError(
                "İnceleme kuyruğu çıktısı yok; eski koşuyu yeni sonuç gibi değerlendirmeyin."
            )
        rows.append(
            {
                "company_id": case.company_id,
                "split": case.split,
                "as_of": analysis.as_of.isoformat(),
                "event": case.target_event_observed,
                "label_source": case.label_source,
                "lead_days": (case.event_date - analysis.as_of).days if case.event_date else None,
                "analysis_sha256": sha,
                "general_outcome": assessment.outcome,
                "review_outcome": assessment.investor_review.status,
                "status": assessment.status,
                "incomplete_checks": assessment.investor_review.incomplete_checks,
            }
        )

    def summarize(selected, field, positive, unknown):
        alerts = [r for r in selected if r[field] == positive]
        abstained = [r for r in selected if r[field] == unknown or r["status"] == "failed"]
        assessed = [r for r in selected if r not in abstained]
        hits = sum(r["event"] for r in alerts if r not in abstained)
        false = sum(not r["event"] for r in alerts if r not in abstained)
        positives = sum(r["event"] for r in selected)
        controls = sum(not r["event"] for r in assessed)
        return {
            "companies": len(selected),
            "assessed": len(assessed),
            "abstained": len(abstained),
            "event_companies": positives,
            "events_flagged": hits,
            "false_alarms": false,
            "effective_event_recall": hits / positives if positives else None,
            "false_positive_rate_among_assessed_controls": false / controls if controls else None,
            "alert_precision_in_this_sample": hits / (hits + false) if hits + false else None,
            "lead_days_of_hits": [
                r["lead_days"] for r in alerts if r["event"] and r not in abstained
            ],
        }

    return {
        "schema_version": "tr-study-1.0",
        "target_definition": study.target_definition,
        "rule_version": study.rule_version,
        "horizon_days": study.horizon_days,
        "rows": rows,
        "results": {
            split: {
                "general_attention": summarize(
                    [r for r in rows if r["split"] == split],
                    "general_outcome",
                    "dikkat_gerektiriyor",
                    "yetersiz_veri",
                ),
                "investor_review": summarize(
                    [r for r in rows if r["split"] == split],
                    "review_outcome",
                    "inceleme_gerekli",
                    "veri_yetersiz",
                ),
            }
            for split in ("development", "test")
        },
        "limitations": [
            "Etiketler kullanıcı/araştırmacı girdisidir; hukuki gerçeklikleri bu komutla doğrulanmadı.",
            "Test ayrımı manifestte beyan edilir; önceki insan/model bilgisinin silindiği kanıtlanamaz.",
            "Örneklem alarm isabeti gerçek piyasa olay sıklığına genellenemez; küçük örneklem kesin başarı değildir.",
            "Partial sonuçlar kapsam eksikleriyle sayılır; yetersiz/failed sonuçlar güvenli şirket sayılmaz.",
            "Finansal veri indirilmedi, veritabanına bağlanılmadı, model çağrılmadı.",
        ],
    }
