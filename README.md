# Bilanco

kodlar src klasöründe 
çıktılar data klasöründe 
gerisi çok önemli değil 

Terminalden çalışan, kaynak ve tarih kontrollü şirket inceleme hattı. İlk sürüm: **Enron Corp., 31 Mart 2000 gün sonu (New York)**. Arayüz, grafik, HTML veya sürekli veri taraması içermez.

Tamamlanan koşunun ayrı, çevrimdışı görsel çıktısı: [Enron HTML demosu](demos/enron-run-88f8d197.html). Dosya kaynak analizi ve son ilişkili işlem değerlendirmesini gösterir; analiz programını çalıştırmaz. [Demo açıklaması](demos/README.md).

Kayıtlı çalışmadan yeni inceleme öncelikleri üretmek için:

```sh
uv run bilanco assess --run-id 88f8d197-9734-480e-9b46-3d374d963b1b
```

Bu komut belge indirmeden ek Codex değerlendirmesi yapar; kaynak çalışma mevcut veritabanında kayıtlı olmalıdır. Yeni `analyze` çalışmalarında bu adım otomatik çalışır. Ayrı JSON/Markdown raporu üretir; eski sonuçları değiştirmez. [Kurallar, bütçe ve sınırlar](docs/assessment.md) · [40 yapay karşı örnek](evaluation/README.md).

```text
analyze komutu
  → çalışma sırasında SEC kaynağı / tarihli arşiv kopyası
  → metin, tablo, konum ve yayın tarihi kontrolleri
  → Python ile sayısal çıkarım ve hesaplar
  → gerektiğinde ayrı Codex çalışması ile kaynak keşfi
  → Codex ile alıntılı ilişki/koşul adayları
  → kod kontrolleri, ayrı inceleme adayları
  → onaylı bulguların AI ile sıralanması
  → analysis.json + report.md
```

## Kurulum

Python 3.12+, [uv](https://docs.astral.sh/uv/), PostgreSQL ve giriş yapılmış [Codex CLI](https://learn.chatgpt.com/docs/non-interactive-mode) gerekir. Bu kişisel, güvenilir yerel kullanım içindir; başka kullanıcılara kendi ChatGPT oturumunu sunucu olarak açmaz.

```sh
uv sync --locked
cp .env.example .env
```

`.env` içindeki `BILANCO_SEC_CONTACT` alanına kendi iletişim e-postanı yaz. SEC, otomatik isteklerde kimliği belirten User-Agent ister. Bu bilgi model paketlerine veya rapora eklenmez. Kimlik/anahtar dosyalarını projeye kopyalama.

**Yerel PostgreSQL zaten çalışıyorsa:**

```sh
createdb bilanco
# Varsayılan bağlantı: postgresql:///bilanco
uv run bilanco db init
```

**Docker ile PostgreSQL 18 kullanacaksan:** `.env` içinde `BILANCO_DB_PASSWORD` belirle ve `BILANCO_DATABASE_URL` değerini `postgresql://bilanco:PAROLAN@localhost:55432/bilanco` olarak ayarla. Paroladaki özel karakterleri URL kurallarına göre kodla.

```sh
docker compose up -d
uv run bilanco db init
```

Veritabanı kurulumu yalnızca boş şemayı oluşturur. Finansal veri eklemez.

```sh
uv run bilanco doctor
```

`doctor` yerel bağlantıyı ve Codex oturum durumunu kontrol eder; finansal belge indirmez, model çağırmaz. Mevcut yerel PostgreSQL 14+ ile aynı SQL şeması kullanılabilir; Compose ve CI hedefi PostgreSQL 18'dir.

## Çalıştırma

**Gerçek veri toplama ve model kullanımı bu komutla başlar:**

```sh
uv run bilanco analyze --company enron --as-of 2000-03-31
```

Kaynakları yeniden indirmek için:

```sh
uv run bilanco analyze --company enron --as-of 2000-03-31 --refresh
```

Toplanan kaynaklar içerik hash'i ile `data/raw/` altında saklanır. Önbellek kullanılmadan önce dosyanın hash'i tekrar kontrol edilir. Başka tarih/şirket henüz desteklenmez; program bu girdileri veri toplamadan reddeder. Kurulumda veya arka planda otomatik indirme yoktur. Önceki elle hazırlanmış HTML, TSV, rapor ve indirilmiş PDF'ler okunmaz.

Çıktılar her çalışmaya özel `data/runs/<run-id>/` altında:

- `analysis.json`: dönemli değişkenler, kesin ondalık değerler, birim/ölçek, kaynak konumları, formüller, bulgular, retler, AI çağrı kayıtları ve aşama süreleri.
- `report.md`: kısa Türkçe açıklamalar, göstergeler, kaynak pasajları ve eksikler.
- `checkpoint.json`: son aşama/durum. Kesilme sonrası aynı analiz tekrar çalıştırılabilir; indirilmiş sağlam dosyalar yeniden kullanılabilir. AI çağrıları tekrar yapılabilir; eski model yanıtları yeni canlı yanıt gibi gösterilmez.
- `ai/`: verilen paketler, şemalı yanıtlar ve kullanım/süre kayıtları. Modelin gizli düşünce metni veya CLI stderr/kimlik bilgileri kaydedilmez.

Önceki çalışmanın çıktısı üzerine yazılmaz. `uv run bilanco runs` son çalışma durumlarını listeler. Yarıda kalan bir süreç kaydı `running` görünebilir; yeni çalışma ayrı kimlik alır. Sürekli açık worker/HTTP sunucusu bu sürümde yoktur; çekirdek fonksiyonlar ileride bunlardan çağrılabilir.

Çıkış kodları: `0` tamamlandı, `3` kısmi çıktı, `1` başarısız, `2` hatalı/eksik yerel ayar.

## Codex ne yapar?

1. Tek keşif turunda en fazla beş ek URL önerebilir. Kod HTTPS/alan adı, şirket, dosyalama türü ve kesim tarihini kontrol etmeden bunları kanıt saymaz.
2. Belge paketlerinden ilişki, garanti, koşul, denetçi görüşü ve dengeleyici şirket açıklaması adaylarını **alıntı ve blok kimliğiyle** çıkarır. Şemada olmayan isim, sayı veya serbest sonuç alanları kabul edilmez. Sayıları Python çıkarır ve hesaplar.
3. Mevcut bulgu kimliklerini sıralar. Sunulan açıklamalar Python şablonlarından gelir; model yeni sayı veya olay yazamaz. Modelin sıraya almadığı mevcut bulgular da raporda kalır. `style` alanı ileriye dönük sunum ipucudur; v1 bütün açıklamaları tam gösterir.

Analiz çağrısı yeni, geçici bir `codex exec` oturumudur. Kendi Codex ayar dosyanız yüklenmez; web, komut, tarayıcı, connector, plugin, bellek ve alt ajan araçları kapatılır. Keşif çağrısında yalnız web araması açılır. Beklenmeyen araç olayı görüldüğünde süreç sonlandırılır ve yanıt kabul edilmez. Araç olayı denetimi tek başına önceki erişimin hiç gerçekleşmediğini kanıtlamaz; kurulumdaki yönetilen politikaların etkisi ayrıca dikkate alınmalıdır.

Bağlantıyı yalnız **hayali bir pasajla** sınamak istersen:

```sh
uv run bilanco check-ai
```

Bu komut bir gerçek model çağrısı kullanır, finansal belge toplamaz. Codex kendi kayıtlı oturumunu kullanır; program `auth.json` okumaz/kopyalamaz. `BILANCO_CODEX_MODEL` isteğe bağlıdır; boşsa CLI varsayılanını çözer. Çağrı başına varsayılan süre sınırı 240 saniye, çalışma başına çağrı sınırı 32'dir. Oturum/kota/model hatasında eldeki Python sonuçları korunur.

## Kanıt ve kapsam sınırları

- İlk yıllık rapor: özgün FY1999 10-K, şirket CIK `0001024401`, accession `0001024401-00-000002`. Bunlar kaynak kimlikleridir; finansal tutarlar kodda bulunmaz.
- Yayın tarihi dosya adı, PDF oluşturulma tarihi, rapor yılı veya indirme zamanından çıkarılmaz. SEC SGML başlığı, SEC indeks kaydı veya SEC submissions metadatası gerekir. Kesimden sonraki dosyalama ve 10-K/A sürümleri yıllık kaynak olarak reddedilir.
- SEC engellenirse erişim kontrolü veya TLS aşılmaz. Arşiv PDF'si için SEC yayın kanıtı ve metin içinden şirket/yıl/sürüm uyumu gerekir. Bu, özgün SEC dosyasıyla byte eşitliği değildir; arşivli çalışma kısmi olarak işaretlenir. Bu sınırlama JSON ve raporda görünür.
- Ek resmî kaynaklar şu anda aynı CIK'e ait, tarihi doğrulanabilen SEC SGML 8-K/10-Q dosyalarıdır. Rastgele haber sitesi, yönetici sosyal medya hesabı veya her türlü web sayfası destekleniyor iddiası yoktur.
- Tablo okuyucu metinli, satır/sütun ilişkisi açık PDF/HTML/SEC metni içindir. Belirsiz sütun, çelişkili tutar, bozuk sayı, eksik birim ve taranmış sayfa tahminle doldurulmaz. OCR ve karmaşık çok kolonlu tablolar için yeni okuyucular eklenebilir.
- `value` basılı tutardır, `scale` çarpanıdır. Örneğin `"value":"200", "scale":1000000` gerçek şirket verisi değil, birim örneğidir. JSON'daki parasal değerler hassasiyet kaybını önlemek için metin olarak kodlanan ondalıklardır; PostgreSQL'de `numeric` sütununda saklanır. `$` bağlamı `dollars` olarak korunur; kendiliğinden ISO `USD` atanmaz. Tire basılı sıfır sayılmaz.
- Alıntının bulunması, AI'ın ilişki yorumunun doğru olduğunu kanıtlamaz. İlişki adayları `needs_review` kalır; otomatik dolandırıcılık hükmüne dönüşmez. Şirketin beyanı bağımsız doğrulama değildir.
- Enron'u bilen modelin eğitim bilgisini silemeyiz. Gelecek belge sızıntısını sınırlamak tamamen kör bir testle aynı şey değildir. Bu uygulama henüz doğrulanmış dolandırıcılık tahmin başarısı sunmaz.
- Genel sonuç etiketi tanımlı kurallardaki inceleme işaretidir. Güvenilirlik yüzdesi, hisse çöküş olasılığı veya al/sat emri üretilmez.

## Testler

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

Testlerde gerçek HTTP bağlantısı engellenir. Belgeler ve şirket pasajları yapaydır; eski Enron çıktıları test cevabı olarak koda gömülmez. CLI adaptörü sahte bir executable ile şema/araç/timeout testinden geçer; `check-ai` ayrı bir canlı bağlantı kontrolüdür, istatistiksel kalite değerlendirmesi değildir.

Gerçek PostgreSQL entegrasyonu için **yalnız teste ait**, adı `bilanco_test_` ile başlayan boş bir veritabanı kullan:

```sh
createdb bilanco_test_local
BILANCO_TEST_DATABASE_URL=postgresql:///bilanco_test_local uv run pytest -q -m postgres
dropdb bilanco_test_local
```

CI aynı testleri PostgreSQL 18 servisiyle çalıştırır. Üretim analizi CI'da başlatılmaz; gerçek SEC isteği/model çağrısı yapılmaz.

## Hız ve Rust

İndirme, kaynak keşfi, tablo çıkarımı, AI çıkarımı, sunum sıralaması ve toplam süre ayrı ölçülür. Henüz gerçek Enron koşusu için performans ölçümü yapılmadı. İlk adım önbellek ve ölçümdür. İşlemciyi yoğun kullanan bir bölüm ölçümle ortaya çıkarsa o bölüm ayrı Rust/PyO3 modülüne taşınabilir; ağ/model bekleme süresini dili değiştirerek ortadan kaldırmayı beklemiyoruz.

## Kaynaklar

- [SEC — EDGAR API ve geçmiş dosyalamalar](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [OpenAI Docs — codex exec ve şemalı çıktı](https://learn.chatgpt.com/docs/non-interactive-mode)
- [OpenAI Docs — araç/yapılandırma seçenekleri](https://developers.openai.com/codex/config-reference/)
- [PostgreSQL — numeric](https://www.postgresql.org/docs/18/datatype-numeric.html)
- [pdfplumber — metin/tablo/konum çıkarımı](https://github.com/jsvine/pdfplumber)
- [PyO3 — Python/Rust paralellik sınırı](https://pyo3.rs/main/parallelism)

### 🌐 Community Wisdom: [Schema-Valid Isn't Correct](https://dev.to/michael_maurice/schema-valid-correct-4-checks-before-you-trust-llm-extraction-4n6f)

> **Source:** [Michael Maurice](https://dev.to/michael_maurice)
>
> **Tags:** `ai`, `architecture`
>
> Yazı, şema doğrulamasından ayrı kaynak ve aritmetik kontrolleri öneriyor. Yorumlarda tekrar eden tutarların yanlış satırla eşleşebileceği vurgulanıyor. Bu nedenle blok/sayfa konumu saklanıyor; anlam doğruluğu ayrıca işaretleniyor. Yazı bir ürün de tanıtıyor; bağımsız Enron başarı deneyi değildir.
>
> 🔗 [Read Full Discussion](https://dev.to/michael_maurice/schema-valid-correct-4-checks-before-you-trust-llm-extraction-4n6f)
