"""Disclosed corporate facts stay distinct from calibrated company-level warnings."""

from .equity_models import Metric, ReviewFinding
from .equity_sources import fold
from .equity_tables import parse_turkish
from .storage import digest

LABELS = {
    "executive_role": "Karşı taraftaki açıklanmış görev",
    "ownership": "Açıklanmış sahiplik ilişkisi",
    "related_purchase": "İlişkili taraftan açıklanmış alış",
    "related_sale": "İlişkili tarafa açıklanmış satış",
    "guarantee": "Açıklanmış teminat / taahhüt",
    "asset_transaction": "Açıklanmış varlık işlemi",
    "treasury_investment": "Açıklanmış finansal yatırım",
}


def evaluate_observations(analysis, current):
    metrics, findings = [], []
    seen = set()
    for obj in analysis.observations:
        # Same statement repeated in context packets is never an extra vote.
        key = (
            obj.kind,
            fold(obj.counterparty),
            obj.person,
            obj.period_end,
            obj.effective_date,
            obj.amount_text,
            obj.basis_date,
            tuple((r.block_id, r.quote) for r in obj.evidence),
            obj.controls.model_dump_json(),
            obj.business_purpose.model_dump_json(),
            tuple((r.block_id, r.quote) for r in obj.counter_evidence),
        )
        if key in seen:
            continue
        seen.add(key)
        ident = digest(repr(key).encode())[:16]
        unknowns = []
        if obj.controls.answer == "unknown":
            unknowns.append(
                "Bu kayıt için onay/değerleme koşulları doğrulanamadı; kontrol yokluğu çıkarılmadı."
            )
        if obj.business_purpose.answer == "unknown":
            unknowns.append("Bu işlemin ekonomik amacı doğrulanamadı.")
        if obj.period_end is None and obj.effective_date is None:
            unknowns.append(
                "Rol/işlemin geçerlilik tarihi belirsiz; başka tarihli işlemle birleştirilmedi."
            )
        used = []
        denominator = {
            "guarantee": "equity",
            "related_sale": "revenue",
            "treasury_investment": "total_assets",
        }.get(obj.kind)
        base = current.get(denominator)
        if (
            base
            and base.value > 0
            and obj.currency == base.currency
            and obj.period_end == base.period_end
            and obj.basis_date == base.basis_date
            and obj.amount_text is not None
        ):
            # This is a stated exposure ratio, never a cash-flow or loss estimate.
            metric_id = f"exposure_{ident}_{denominator}"
            metrics.append(
                Metric(
                    id=metric_id,
                    domain="relations",
                    value=parse_turkish(obj.amount_text) / base.value,
                    unit="ratio",
                    formula=f"disclosed_{obj.kind} / {denominator}",
                    fact_ids=[base.id],
                    source_ids=sorted(
                        {
                            base.source_id,
                            *[
                                b.source_id
                                for b in analysis.blocks
                                if any(r.block_id == b.id for r in obj.evidence)
                            ],
                        }
                    ),
                )
            )
            used.append(metric_id)
        transaction = obj.kind in {
            "related_purchase",
            "related_sale",
            "guarantee",
            "asset_transaction",
        }
        # Missing approval is UNKNOWN. Only an explicit, grounded absence statement
        # creates a review candidate; this new policy is non-voting pending calibration.
        review = transaction and obj.controls.answer in {"no", "conflicting"}
        findings.append(
            ReviewFinding(
                id=f"OBS-{ident}",
                rule_id="R02" if review else "R-OBS",
                domain="relations",
                level="review" if review else "context",
                title=f"{LABELS[obj.kind]}: {obj.counterparty}",
                explanation=(
                    "Kaynakta kontrol eksikliği/çelişkisi beyanı var; işlemin koşulları ayrıca incelenmeli. "
                    "Yeni politika kalibre edilmediği için genel şirket sonucuna ek oy verilmedi."
                    if review
                    else "Kaynaklı ilişki/maruziyet bilgisi. İlişkili olmak veya teminat vermek tek başına olumsuz işaret sayılmadı."
                ),
                metric_ids=used,
                evidence=list(
                    {
                        (r.block_id, r.quote): r
                        for r in [
                            *obj.evidence,
                            *obj.controls.evidence,
                            *obj.business_purpose.evidence,
                        ]
                    }.values()
                ),
                counter_evidence=obj.counter_evidence,
                unknowns=unknowns,
                contributes_to_outcome=False,
            )
        )
    return metrics, findings
