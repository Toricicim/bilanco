"""Small terminal menu. Selection returns the same explicit analyze arguments."""

from datetime import datetime

from .equity_models import COMPANIES, ISTANBUL
from .equity_text import PROMPT_VERSION
from .terminal import print_equity_summary


def choice(prompt, allowed, *, read, write, default=None):
    while True:
        value = read(prompt).strip()
        if not value and default is not None:
            value = default
        if value in allowed:
            return value
        write("Geçerli seçeneklerden birini yazın: " + ", ".join(allowed))


def choose_start(settings, store, *, read=input, write=print):
    write("\nBİLANCO — Türkiye hisse incelemesi")
    companies = list(COMPANIES)
    for i, key in enumerate(companies, 1):
        write(f"  {i}) {COMPANIES[key].name} ({COMPANIES[key].ticker})")
    write("  0) Çıkış")
    picked = choice(
        "Şirket [1]: ",
        ["0", *map(str, range(1, len(companies) + 1))],
        read=read,
        write=write,
        default="1",
    )
    if picked == "0":
        return None
    company_id = companies[int(picked) - 1]
    previous = store.find_equity_run(company_id, prompt_version=PROMPT_VERSION)
    today = datetime.now(ISTANBUL).date()
    default_date = previous[0].as_of if previous else today
    while True:
        value = read(f"Bilgi kesimi YYYY-AA-GG [{default_date}] (0: çıkış): ").strip()
        if value == "0":
            return None
        try:
            as_of = datetime.strptime(value, "%Y-%m-%d").date() if value else default_date
            if not COMPANIES[company_id].listed_at <= as_of <= today:
                raise ValueError
            break
        except ValueError:
            write("Halka arzdan bugüne kadar geçerli bir tarih yazın; örnek: 2025-03-31.")
    if previous is None or previous[0].as_of != as_of:
        previous = store.find_equity_run(company_id, as_of=as_of, prompt_version=PROMPT_VERSION)
    base = previous[0].ai.get("packets_processed", 0) if previous else 0
    planned = previous[0].ai.get("packets_planned", 0) if previous else 0
    if previous and planned > 0 and base >= planned:
        write("Bu tarih için eldeki bütün paketler işlenmiş. Kayıtlı sonucu gösteriyorum.")
        print_equity_summary(
            previous[0], previous[1], settings.data_dir / "runs" / previous[0].run_id, write=write
        )
        write("Yeni kaynak edinmek için analyze komutuyla yeni bir çalışma başlatabilirsiniz.")
        return None
    if previous:
        write(f"Aynı şirket/tarihte en fazla taranmış yerel kayıt: {base}/{planned} paket.")
        write("Kaç paket daha ekleyelim? (Mevcut tarihli kaynaklardan devam edilir.)")
    else:
        write("Bu şirket/tarih için uyumlu yerel kayıt yok. Kaç paketle başlayalım?")
    for i, amount in enumerate((10, 20, 40), 1):
        effective = min(amount, max(0, planned - base)) if planned else amount
        budget = min(128, 2 * effective + (0 if previous else 2))
        write(f"  {i}) {amount} paket — en fazla {budget} AI çağrısı (tekrarlar dahil)")
    write("  0) Çıkış")
    picked = choice("Paket seçimi [1]: ", ["0", "1", "2", "3"], read=read, write=write, default="1")
    if picked == "0":
        return None
    amount = (10, 20, 40)[int(picked) - 1]
    if planned:
        amount = min(amount, max(0, planned - base))
    target = base + amount
    calls = min(128, 2 * amount + (0 if previous else 2))
    write(
        f"\nBaşlıyor: {base} önceki + {amount} yeni = hedef {target} paket; çağrı tavanı {calls}."
    )
    write(
        "Paket sayısı belge veya çağrı sayısı değildir. Kalan kapsam ve süreler bitişte gösterilecek."
    )
    args = [
        "analyze",
        "--company",
        company_id,
        "--as-of",
        as_of.isoformat(),
        "--max-packets",
        str(target),
        "--max-ai-calls",
        str(calls),
    ]
    if previous:
        args += ["--resume-run", previous[0].run_id, "--offline", "--no-discover"]
    return args
