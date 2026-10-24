# Bilanco

Terminalden çalışan, kaynak ve tarih kontrollü şirket inceleme hattı. Belgelerden alıntılı bulgular, finansal göstergeler ve yatırım öncesi inceleme işaretleri çıkarır. Dolandırıcılık hükmü veya al/sat emri üretmez. Kod `src/`, yerel çıktılar `data/`, paylaşılabilir sabit HTML örnekleri `demos/` klasöründedir. Program HTML üretmez ve arka planda sürekli tarama yapmaz.

## Hızlı başlatma

İlk kez kullanıyorsan aşağıdaki [kurulumu](#kurulum) tamamla. Sonraki çalıştırmalarda repo klasöründe tek komut yeterli:

```sh
./baslat
```

Aynı menü `uv run bilanco` veya `uv run bilanco start` ile de açılır.

1. Şirketi seç: **OZATD, HATSN veya KERVN**.
2. Bilgi kesim tarihini seç. Önceki uyumlu çalışma varsa onun tarihi, yoksa bugün önerilir. Geçmiş incelemede araştırmak istediğin eski tarihi yaz.
3. Paket sayısını seç:

| Seçim | Paket |
| --- | --- |
| `1` | 10 |
| `2` | 20 |
| `3` | 40 |
| `0` | Çıkış |

Aynı şirket ve tarihte kayıt yoksa **“Kaç paketle başlayalım?”**, varsa **“Kaç paket daha ekleyelim?”** sorulur. Örneğin 70 paketlik kayıt varken `3` seçmek toplam hedefi 110 yapar. Kalan paket sayısı daha azsa yalnız kalanlar alınır. Havuz tamamen okunmuşsa kayıtlı sonuç gösterilir.

Menü, yerel veritabanındaki aynı şirket/tarihe ait uyumlu tamamlanmış veya kısmi çalışmaların en fazla paket işlenmiş olanını seçer. Devam ederken önceki kaynakları doğrulayıp kullanır; finansal belgeleri yeniden indirmez, web keşfi yapmaz. AI bağlantısı yine gerekir. Farklı bir tarih seçersen o tarihe ait kayıt aranır. Yeni kaynak toplamak veya Enron çalıştırmak için aşağıdaki `analyze` komutlarını kullan.

Seçeneklerde **tekrarlar dahil azami AI çağrısı** da görünür: devamda 10/20/40 paket için 20/40/80; ilk çalışmada web keşfi payıyla 22/42/82. Bu menü bütçesi `.env` varsayılanını o çalışma için değiştirir. Paket sayısı belge veya çağrı sayısı değildir. Paket seçimi analizi başlatır; `0` veya seçim sırasında Ctrl+C ile çıkabilirsin.

Bitişte önemli inceleme işaretleri, karşı açıklamalar, eksik kapsam, yeni çağrı/önbellek sayısı ve **her aşamanın dakika–saniye süresi** terminalde gösterilir. Bağlam kayıtları büyük alarm gibi sunulmaz; işaret bulunmaması güvenli olduğu anlamına gelmez.

## Desteklenen analizler

**Türkiye desteği:** OZATD, HATSN ve KERVN için aynı KAP/Türkçe tablo/fiyat-hacim analiz akışı kullanılır. OZATD/HATSN geçmiş tarama çalışmaları ayrıca vardır. Enron komutu ve kayıtları korunur. Türkiye komutları SEC e-postası istemez. [Kullanım, belge aktarımı ve sınırlar](docs/turkiye.md).

2026-10-18: ad/alıntı doğrulama, finansal ekler ve kapsam takibi düzeltildi; ilişkili işlem/teminat/görev gözlemleri ayrı kaydedilir. Normal veya belirsiz ilişkili işlemler otomatik şirket alarmı sayılmaz. Yeni inceleme adayları, kalibrasyona kadar genel sonuca oy vermez. [v2 davranışı, yanlış alarm kontrolleri ve deney protokolü](docs/turkey-review-v2.md).

**v3 temeli:** 15 yatırımcı gözlemi, kaynaklı sorun/karşı açıklamalar, ilişkili alacak–stok–kâr bileşeni–nakit köprüsü ölçümleri ve açık eksik veri listesi eklendi. KERVN'nin eski nominal raporları için ayrı muhasebe esası doğrulanır. [Nelerin hesaplandığı, eksikler ve KERVN kullanımı](docs/investor-checks.md). Gerçek KERVN analizi henüz çalıştırılmadı.

**Güncel v4:** AI'ın kaynaklı nötr olgularından plan/gerçekleşme ve sözleşme tarafı karşılaştırmaları, doğrulanan paket yönlendirmeleriyle fon/likidite izi, dönemli kâr/nakit geçmişi ve görünür yatırım öncesi inceleme kuyruğu eklendi. `evaluate-study` kayıtlı sonuçlarda yakalama/yanlış alarmı HTTP/AI/DB kullanmadan ölçer. [Kullanım, kaynak şartları ve sınırlar](docs/early-review-v4.md). Gerçek şirketlerde yeni sürüm başarısı henüz ölçülmedi; otomatik bütün fon kaynaklarını keşfetmez.

**Kaynak keşfi/model yönlendirme:** Türkiye `analyze`, tarih ve kimlik doğrulanan KAP kaynak önerileri için ayrı web çağrısı kullanır; çıkarımda web kapalıdır. Doğrudan `analyze` komutunda varsayılan toplam 30 paket; menüde seçtiğin sayı geçerlidir. Hafif model ve yeni yanıttaki doğrulama hatasında tek güçlü tekrar kullanılır. [Komutlar, bütçe ve sınırlar](docs/source-discovery-routing.md).

31 Mart 2025 kesimli [güncel Özata HTML demosu](demos/ozatd-2025-03-31.html): v4 inceleme mesajı, iki finansal işaret, IBG/PPZ fon pozisyonları ve açık eksikler. AI kapsamı **70/141 paket**. Ek 40 pakette şirketin 6 Ocak 2025 tarihli, basında atfedilen iş ortaklığının hâkim ortağına ait olduğunu belirten açıklaması bulundu. Bu dengeleyici bir bağlam kaydıdır; yeni risk alarmı değildir. Önceki 30 paketlik koşuda web keşfi uygun yeni kaynak önermedi; son devam koşusunda keşif kapalıydı. Genel sonuç hâlâ sınırlı işaret; tam tarama başarısı değildir. Dosya tek başına paylaşılabilir; eski v1 gösterimi Git geçmişinde korunur.

```sh
uv run bilanco analyze --company ozatd --as-of 2025-03-31
uv run bilanco analyze --company kervn --as-of 2016-03-31
uv run bilanco replay --company ozatd --study pre-2025-spk
uv run bilanco replay --company ozatd --study pre-2026-funds
```

Kaynak erişilemezse sonuç kısmi/yetersiz veri olur; eksik belge risk yok anlamına gelmez. `--bundle ./belgeler` ile tarih kontrollü KAP PDF/CSV aktarımı, `--offline` ile finansal HTTP yapmadan paket incelemesi desteklenir. Yeni yerel sonuçlar `data/runs/` ve `data/replays/` altında saklanır; Git'e eklenmez. Önceden paylaşılmış Enron snapshot dosyaları korunur.

Tamamlanan koşunun ayrı, çevrimdışı görsel çıktısı: [Enron HTML demosu](demos/enron-run-88f8d197.html). Dosya kaynak analizi ve son ilişkili işlem değerlendirmesini gösterir; analiz programını çalıştırmaz. [Demo açıklaması](demos/README.md).

Kayıtlı çalışmadan yeni inceleme öncelikleri üretmek için:

```sh
uv run bilanco assess --run-id 88f8d197-9734-480e-9b46-3d374d963b1b
```

Bu komut belge indirmeden ek Codex değerlendirmesi yapar; kaynak çalışma mevcut veritabanında kayıtlı olmalıdır. Yeni `analyze` çalışmalarında bu adım otomatik çalışır. Ayrı JSON/Markdown raporu üretir; eski sonuçları değiştirmez. [Kurallar, bütçe ve sınırlar](docs/assessment.md) · [48 yapay regresyon örneği](evaluation/README.md).

Enron akışı:

```text
analyze komutu
  → çalışma sırasında özgün SEC kaynağı (sürümü doğrulanmamış arşiv hariç)
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
# Yalnız ilk kurulumda; mevcut .env dosyanın üzerine yazma:
[ -f .env ] || cp .env.example .env
```

Enron analizi için `.env` içindeki `BILANCO_SEC_CONTACT` alanına kendi iletişim e-postanı yaz. SEC, otomatik isteklerde kimliği belirten User-Agent ister. Bu bilgi model paketlerine veya rapora eklenmez. Kimlik/anahtar dosyalarını projeye kopyalama.

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

Veritabanı kurulumu yalnızca boş şemayı oluşturur. Finansal veri eklemez. Repoyu indiren herkes kendi PostgreSQL veritabanını, `.env` ayarlarını ve Codex oturumunu kullanır. Bizim yerel çalışma kayıtlarımız Git ile gelmez; arkadaşlarının ilk menüsü yeni analizle başlar. HTML demosunu açmak için bunların hiçbiri gerekmez.

```sh
uv run bilanco doctor
```

`doctor` yerel bağlantıyı ve Codex oturum durumunu kontrol eder; finansal belge indirmez, model çağırmaz. Mevcut yerel PostgreSQL 14+ ile aynı SQL şeması kullanılabilir; Compose ve CI hedefi PostgreSQL 18'dir.

## Paket ekleme ve otomasyon

Menü yerine bütün parametreleri kendin verebilirsin. `--max-packets` eklenecek sayıyı değil, **toplam işlenecek paket hedefini** belirtir:

```sh
# Yeni analiz: toplam 20 paket, keşif ve tekrarlar dahil en fazla 42 çağrı
./baslat analyze --company ozatd --as-of 2025-03-31 --max-packets 20 --max-ai-calls 42

# Yerel 30 paketlik kayda 40 daha ekle: ONCEKI_UUID yerine kendi kayıt kimliğini yaz
./baslat analyze --company ozatd --as-of 2025-03-31 \
  --resume-run ONCEKI_UUID --max-packets 70 --max-ai-calls 80 --offline --no-discover
```

Önbellekteki yanıtlar yeniden kanıt doğrulamasından geçer; geçmeyen adaylar reddedilir. Önceden reddedilmiş aday için her devamda yeniden güçlü model çağrısı yapılmaz. Bunu özellikle denemek istersen `--retry-cached` ekle ve bütçeyi buna göre belirle. Yeni paketten gelen doğrulama hatasında tek güçlü tekrar korunur.

Menü açık bir terminal ister; otomasyon/boru hattında beklemek yerine hata verir. `analyze` komutunda makine tarafından okunacak JSON standart çıktıya, insan özeti standart hataya yazılır. Örneğin `... > sonuc.json` çıktısı JSON olarak kalır. Menüde yalnız insan özeti gösterilir.

## Enron çalıştırma

**Gerçek veri toplama ve model kullanımı bu komutla başlar:**

```sh
uv run bilanco analyze --company enron --as-of 2000-03-31
```

Kaynakları yeniden indirmek için:

```sh
uv run bilanco analyze --company enron --as-of 2000-03-31 --refresh
```

Toplanan kaynaklar içerik hash'i ile `data/raw/` altında saklanır. Önbellek kullanılmadan önce dosyanın hash'i tekrar kontrol edilir. Enron akışında başka tarih desteklenmez; Türkiye hisseleri için yukarıdaki komutları kullan. Kurulumda veya arka planda otomatik indirme yoktur. Önceki elle hazırlanmış HTML, TSV, rapor ve indirilmiş PDF'ler okunmaz.

Çıktılar her çalışmaya özel `data/runs/<run-id>/` altında:

- `analysis.json`: dönemli değişkenler, kesin ondalık değerler, birim/ölçek, kaynak konumları, formüller, bulgular, retler, AI çağrı kayıtları ve aşama süreleri.
- `report.md`: kısa Türkçe açıklamalar, göstergeler, kaynak pasajları ve eksikler.
- `assessment.json`: Türkiye akışında kuralların değerlendirmesi, bulgular ve yatırım öncesi inceleme mesajı. Enron ek değerlendirmesinin dosya yolları komut çıktısında ayrıca verilir.
- `checkpoint.json`: son aşama/durum; yeni Türkiye çalışmalarında kayıt işlemi ve toplam duvar süresi de burada bulunur. Kesilme sonrası aynı analiz tekrar çalıştırılabilir; indirilmiş sağlam dosyalar yeniden kullanılabilir. AI çağrıları tekrar yapılabilir; eski model yanıtları yeni canlı yanıt gibi gösterilmez.
- `ai/`: verilen paketler, şemalı yanıtlar ve kullanım/süre kayıtları. Modelin gizli düşünce metni veya CLI stderr/kimlik bilgileri kaydedilmez.

Önceki çalışmanın çıktısı üzerine yazılmaz. `uv run bilanco runs` son çalışma durumlarını listeler. Yarıda kalan bir süreç kaydı `running` görünebilir; yeni çalışma ayrı kimlik alır. Sürekli açık worker/HTTP sunucusu bu sürümde yoktur; çekirdek fonksiyonlar ileride bunlardan çağrılabilir.

Çıkış kodları: `0` tamamlandı/menüden çıkıldı, `3` kısmi çıktı (rapor oluşabilir), `1` başarısız, `2` hatalı/eksik yerel ayar, `130` kullanıcı iptali.

## Codex ne yapar?

1. Tek keşif turunda en fazla beş ek URL önerebilir. Kod HTTPS/alan adı, şirket, dosyalama türü ve kesim tarihini kontrol etmeden bunları kanıt saymaz.
2. Belge paketlerinden ilişki, garanti, koşul, denetçi görüşü ve dengeleyici şirket açıklaması adaylarını **alıntı ve blok kimliğiyle** çıkarır. Şemada olmayan isim, sayı veya serbest sonuç alanları kabul edilmez. Sayıları Python çıkarır ve hesaplar.
3. Mevcut bulgu kimliklerini sıralar. Sunulan açıklamalar Python şablonlarından gelir; model yeni sayı veya olay yazamaz. Modelin sıraya almadığı mevcut bulgular da raporda kalır. `style` alanı ileriye dönük sunum ipucudur; v1 bütün açıklamaları tam gösterir.

Analiz çağrısı yeni, geçici bir `codex exec` oturumudur. Kendi Codex ayar dosyanız yüklenmez; web, komut, tarayıcı, connector, plugin, bellek ve alt ajan araçları kapatılır. Keşif çağrısında yalnız web araması açılır. Beklenmeyen araç olayı görüldüğünde süreç sonlandırılır ve yanıt kabul edilmez. Araç olayı denetimi tek başına önceki erişimin hiç gerçekleşmediğini kanıtlamaz; kurulumdaki yönetilen politikaların etkisi ayrıca dikkate alınmalıdır.

Bağlantıyı yalnız **hayali bir pasajla** sınamak istersen:

```sh
uv run bilanco check-ai
```

Bu komut bir gerçek model çağrısı kullanır, finansal belge toplamaz. Codex kendi kayıtlı oturumunu kullanır; program `auth.json` okumaz/kopyalamaz. `BILANCO_CODEX_MODEL` isteğe bağlıdır; boşsa Enron CLI varsayılanını, Türkiye analyze `gpt-6-luna` seçer (güçlü tekrar `gpt-6.1-sol`). Çağrı başına varsayılan süre sınırı 240 saniye, çalışma başına çağrı sınırı 32'dir. Oturum/kota/model hatasında eldeki Python sonuçları korunur.

## Kanıt ve kapsam sınırları

- İlk yıllık rapor: özgün FY1999 10-K, şirket CIK `0001024401`, accession `0001024401-00-000002`. Bunlar kaynak kimlikleridir; finansal tutarlar kodda bulunmaz.
- Yayın tarihi dosya adı, PDF oluşturulma tarihi, rapor yılı veya indirme zamanından çıkarılmaz. SEC SGML başlığı, SEC indeks kaydı veya SEC submissions metadatası gerekir. Kesimden sonraki dosyalama ve 10-K/A sürümleri yıllık kaynak olarak reddedilir.
- SEC engellenirse erişim kontrolü veya TLS aşılmaz. Başka arşivdeki PDF'nin aynı tarihsel sürüm olduğu ayrıca kanıtlanamadığından bu sürümde analize alınmaz. Eski SEC metadata tarihi tek başına kopyayı doğrulamaz; eksik kaynak başarısız/kısmi kapsam olarak görünür.
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

Yeni Türkiye çalışmalarında hazırlık/önceki kaydı doğrulama, kaynak yükleme, tablo okuma, AI çıkarımı ve kanıt doğrulama, ek kaynak keşfi, hesap/kurallar ve kayıt süreleri ayrı ölçülür. Terminal dakika–saniye, JSON saniye cinsinden verir. Her AI paketinin süresi de denetim kaydına eklenir. Eski kayıtlarda bulunmayan aşama süreleri “ölçülmedi” gösterilir; sonradan tahmin edilmez. `analysis.json` analiz sürelerini, `checkpoint.json` ayrıca kayıt ve toplam duvar süresini saklar. İşlemciyi yoğun kullanan bir bölüm ölçümle ortaya çıkarsa o bölüm ayrı Rust/PyO3 modülüne taşınabilir; ağ/model bekleme süresini dili değiştirerek ortadan kaldırmayı beklemiyoruz.

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


## 2026-10-16 inceleme düzeltmeleri

Yeni değerlendirmeler `related-party-2` kurallarını ve Assessment 1.1'i kullanır. [Düzeltme ve doğrulama kaydı](docs/review-fixes.md) · [Kurallar ve sınırlar](docs/assessment.md). Sürümü doğrulanmamış arşiv PDF'si finansal girdiye alınmaz; SEC özgün dosyası yoksa kapsam eksik kalır. İptalde kısmi kayıt korunur, yeni AI aşaması başlamaz (çıkış 130). Negatif özkaynak ayrıca görünür; belirsiz used-in nakit işareti olumlu yorumlanmaz.

[Değerlendirme komutları](evaluation/README.md) dört öncelik sınıfını, gereksiz incelemeleri ve ham bloklardan ilk aday çıkarımındaki kaçırmaları ölçebilir. 48 pasaj yapay regresyon setidir; insan etiketleri henüz tamamlanmadı. Önceki Enron HTML/JSON dosyaları **related-party-1 tarihsel snapshot'ıdır**; bu kod düzeltmelerinin yeniden çalıştırılmış sonucu değildir.
