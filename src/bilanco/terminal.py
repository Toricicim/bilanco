"""Human-readable results; machine-readable analyze stdout stays JSON."""

import json
import math


def duration(seconds):
    if seconds is None:
        return "ölçülmedi"
    seconds = float(seconds)
    if not math.isfinite(seconds) or seconds < 0:
        return "ölçülmedi"
    rounded = int(seconds + 0.5)
    minutes, seconds = divmod(rounded, 60)
    return f"{minutes} dk {seconds:02d} sn"


def saved_timings(directory, analysis):
    result = dict(analysis.timings)
    try:
        checkpoint = json.loads((directory / "checkpoint.json").read_text())
        if checkpoint.get("run_id") == analysis.run_id:
            result.update(checkpoint.get("timings", {}))
    except (OSError, ValueError, TypeError):
        pass
    return result


def print_equity_summary(analysis, assessment, directory, *, write=print, timings=None):
    timings = timings if timings is not None else saved_timings(directory, analysis)
    write("\n" + "=" * 60)
    write(f"SONUÇ — {analysis.company} / {analysis.as_of}")
    candidates = [f for f in assessment.findings if f.level in {"critical", "review"}]
    critical = [f for f in candidates if f.level == "critical"]
    if critical:
        write(f"!!! KRİTİK İNCELEME İŞARETİ: {len(critical)} !!!")
    elif candidates:
        write(f"DİKKAT — {len(candidates)} YATIRIM ÖNCESİ İNCELEME İŞARETİ")
    else:
        write("Değerlendirilen veride önemli inceleme işareti üretilmedi.")
    if assessment.investor_review:
        write(assessment.investor_review.message)
    ordered = sorted(candidates, key=lambda f: f.level != "critical")
    for finding in ordered[:10]:
        write(f"\n[{finding.level.upper()} / {finding.rule_id}] {finding.title}")
        write(finding.explanation)
        if finding.counter_evidence:
            write("Karşı açıklama: " + finding.counter_evidence[0].quote)
        if finding.unknowns:
            write("Bilinmeyen: " + "; ".join(finding.unknowns))
        write(
            "Genel sonuca dahil: "
            + ("evet" if finding.contributes_to_outcome else "hayır; inceleme adayı")
        )
    if len(ordered) > 10:
        write(f"Diğer {len(ordered) - 10} işaret raporda.")
    write(f"\nGenel sonuç: {assessment.outcome} | Çalışma: {analysis.status}")
    processed, planned = (
        analysis.ai.get("packets_processed", 0),
        analysis.ai.get("packets_planned", 0),
    )
    write(f"Paketler: {processed}/{planned} işlendi; {max(0, planned - processed)} okunmadı.")
    if analysis.ai.get("resumed_from"):
        previous = analysis.ai.get("resume_extraction_packets", 0)
        write(
            f"Başlangıç kaydı: {previous} paket. İşlenen toplam farkı: {processed - previous:+d}."
        )
    write(
        f"AI: {analysis.ai.get('calls', 0)} yeni çağrı; {analysis.ai.get('cache_hits', 0)} önbellek kullanımı."
    )
    rejected = sum(r.get("rejections", 0) for r in analysis.ai.get("packet_manifest", []))
    failures = sum(r.get("status") == "failed" for r in analysis.ai.get("receipts", []))
    if rejected or failures:
        write(f"Doğrulama: {rejected} reddedilen AI adayı; {failures} başarısız model çağrısı.")
    if analysis.status != "complete":
        write("Kapsam kısmi. Eksik veri veya işaret bulunmaması güvenlik sonucu değildir.")
    write("\nSÜRELER")
    for key, label in (
        ("preparation", "Hazırlık / önceki kaydı doğrulama"),
        ("acquisition", "Kaynak edinimi / yerel kaynak yükleme"),
        ("table_extraction", "Tablo okuma"),
        ("ai_extraction", "AI metin okuma ve kanıt doğrulama"),
        ("source_discovery", "Ek kaynak araması"),
        ("rule_evaluation", "Hesaplama ve risk kuralları"),
        ("persistence", "Dosya ve veritabanına kayıt"),
    ):
        write(f"  {label}: {duration(timings.get(key))}")
    if "wall_total" in timings:
        write("  TOPLAM: " + duration(timings["wall_total"]))
    else:
        write("  Analiz toplamı (kayıt hariç): " + duration(timings.get("total")))
    write(f"\nRapor: {directory / 'report.md'}")
    write(f"Ana çıktı: {directory / 'analysis.json'}")
    write(f"Değerlendirme: {directory / 'assessment.json'}")
    write("=" * 60)
