# Türkiye hisseleri: tarihli inceleme

Güncelleme: 2026-10-16. Desteklenen ilk hisseler OZATD ve karşılaştırma vakası HATSN. Enron'un `2000-03-31` komutu, çıktı biçimleri ve kayıtları korunur. Python/PostgreSQL/Codex altyapısı ortaktır; kaynak ve tablo okuyucuları piyasaya göre ayrıdır. Yeni bir model eğitilmez.

## Çalıştırma

```sh
uv run bilanco analyze --company ozatd --as-of 2025-03-31
uv run bilanco replay --company ozatd --study pre-2025-spk
uv run bilanco replay --company ozatd --study pre-2026-funds
uv run bilanco analyze --company hatsn --as-of 2025-03-31
```

Türkiye komutları SEC iletişim e-postası istemez. PostgreSQL ve mevcut Codex oturumu kullanılır. KAP web bağlantısı ve Yahoo bağlantısı ücretsiz erişim denemeleridir; resmî sözleşmeli API hizmeti veya kesintisiz erişim garantisi değildir. TLS/403/429 engelleri aşılmaz, güvenlik doğrulaması kapatılmaz. Bağlantı hatası rapora yazılır. Çıkış `0`: tamamlandı, `3`: kısmi, `1`: veri/çalışma başarısız, `130`: iptal. Kısmi çalışmada da JSON/Markdown saklanır. `--refresh` HTTP önbelleğini yeniler; eski ham baytlar silinmez.

**Paketle devam:**

```sh
uv run bilanco analyze --company ozatd --as-of 2025-03-31 --bundle ./belgeler
# Finansal HTTP isteklerini tamamen kapatmak için (Codex hâlâ internet kullanabilir):
uv run bilanco analyze --company ozatd --as-of 2025-03-31 --bundle ./belgeler --offline
uv run bilanco replay --company ozatd --study pre-2025-spk --bundle ./belgeler --offline
```

Veri toplama yalnız bu açık komutlarla başlar; import, kurulum ve `doctor` finansal veri çekmez. `replay` kaynakları son kesime kadar bir kez edinir, her değerlendirmeden önce belge ve fiyatları ayrı filtreler. Sonraki aylardaki bilgiler önceki AI paketlerine girmez.

## Belge paketi

Bir klasöre KAP bildirim sayfasındaki **KAP PDF** çıktısını indir. Sadece şirketin tarih yazan bağımsız denetim eki yeterli değildir: bildirim kimliği ve KAP yayın zamanı da kanıtlanmalıdır. Örneğin 2024 raporunun KAP PDF adresi:

https://www.kap.org.tr/tr/api/BildirimPdf/1399375

Klasörde `manifest.json` oluştur:

```json
{
  "schema_version": "1.0",
  "company": "ozatd",
  "documents": [
    {"disclosure_id": 1399375, "file": "KAP-1399375.pdf"}
  ],
  "market": [],
  "bulletins": []
}
```

Program dosyada şirketi, kalıcı `Bildirim/ID` bağlantısını ve `KAP'ta yayınlanma tarihi ve saati` bilgisini kontrol eder. Manifestten yayın tarihi veya finansal değer kabul etmez. Dosyaların paket dışına çıkmasına izin vermez. Sonradan yayımlanan/düzeltme tarihli dosya erken kesime alınmaz. Manuel dosyanın gerçekten sunucudan indirildiği çevrimdışı kriptografik olarak kanıtlanamaz; bu sınırlama her kaynakta kaydedilir. Bu bir noter/onaylı arşiv doğrulaması değildir.

**Dipnot ekleri:** KAP bildirim PDF'si tam dipnotları içermeyebilir. Otomatik edinim aynı bildirimin `attachment-detail` metadata kaydını alıp bağlantılı PDF eklerini de indirir. Manuel aktarımda ilgili metadata JSON'unu da kaydet:

`https://www.kap.org.tr/tr/api/notification/attachment-detail/1399375`

Belge girdisine `"detail_file": "detail.json"` ve `"attachments": {"KAP_METADATA_OBJID": "metadata-ile-ayni-dosya-adi.pdf"}` ekle. ObjId, dosya adı, bildirim kimliği ve yayın zamanı eşleşmelidir. Bağlanamayan ek analize alınmaz. OCR yok; okunamayan sayfalar ve boyut sınırları görünür eksiktir. Kaynak metadata dosyası ve ekin geçmiş bayt sürümü bağımsız arşiv ispatı değildir.

SPK bülteni de `"bulletins": [{"file": "2025-28.pdf", "url": "https://spk.gov.tr/data/68126e9e8f95db0ba8ec02f2/2025-28.pdf"}]` biçiminde aktarılabilir. Bültenin kendi kapak tarihi ve numarası doğrulanır, sadece ilgili şirket bölümü modele gönderilir. Tarihi gün kesinliğinde olan bülten ancak ertesi gün kullanılabilir.

**Piyasa CSV:** Her sembol için ayrı dosya kullan; UTF-8 ve aşağıdaki başlıklar zorunlu:

```csv
date,symbol,close,volume
```

Her satırda ISO tarih (`2025-03-31`), `OZATD.IS` veya `XU100.IS`, noktalı ondalık kapanış ve varsa işlem miktarı yazılı olmalı. Sayılar TRY cinsinde; hacim pay adedi olmalıdır. Manifestin `market` listesinde her dosya için `symbol`, `file`, gerçek HTTPS kaynak `url` ve `price_basis` (`as_traded` veya `provider_adjusted`) bulunur. Veri kaynağının düzeltme biçimi bilinmiyorsa nominal fiyat beyan etme. Günlük hacmi işlem tutarıyla karıştırma. Sonraki tarihlerdeki satırlar hesaplardan önce dışlanır. Çelişen mükerrer gün reddedilir. Boş hacim sıfır sayılmaz.

Yahoo geçmiş fiyatları bugünden yeniden oluşturulur; geçmiş düzeltme sürümü doğrulanmadığından **nominal piyasa değeri/FK hesaplanmaz**. Fiyatlar eksikse veya son gözlem 7 günden eskiyse piyasa kapsamı tamamlandı sayılmaz. Derinlik ve nihai yatırımcı kimlikleri bu kaynaklardan elde edilmiş gibi gösterilmez.

## Uyarılar ve AI

Akış: tarih kontrolü → Türkçe tablo çıkarımı → Python hesapları → alıntılı AI çıkarımı ve karşı açıklamalar → Python değerlendirmesi.

`tr-equity-review-1` eşikleri vaka sonucuna göre otomatik ayarlanmaz:

| Kural | Koşul | Alan |
|---|---|---|
| F01 | Net kâr pozitif, faaliyet nakdi negatif | Finansal |
| F02 | Özkaynak negatif | Doğrudan dikkat |
| F03 | Nakit/(kısa finansal borç + uzun borcun kısa kısmı) < 0,25 ve faaliyet nakdi negatif | Finansal |
| F05 | Alacak gün vekilinde ≥30 gün artış ve alacak büyümesi–satış büyümesi ≥20 puan | Finansal |
| O01 | Aynı satın alma gücüyle satış değişimi ≤−%20 ve faaliyet marjı farkı ≤−5 puan | Faaliyet |
| O02 | Açık satış tahmininin gerçekleşmesi <%80; dönem/para birimi/satın alma gücü aynı | Faaliyet |
| M01 | 60 işlem gününde getiri ≥%100 ve BIST 100 farkı ≥50 puan | Piyasa |
| İlişki | Tek gerçekleşmiş işlem + açık yönetici bağlantısı + aynı taraflar | İlişkiler |
| Denetim | Açık olumsuz görüş, görüş vermekten kaçınma veya şirkete özgü önemli süreklilik belirsizliği | Doğrudan dikkat |

Alacak gün vekili = dönem sonu ticari alacak × dönem gün sayısı / satış. Ortalama alacak veya gerçek gecikmiş fatura ölçümü değildir; raporda bu adla gösterilir. İki karşılaştırılabilir alacak tarihi yoksa hesaplanmaz. Dört sütunlu ara dönem gelir tablosunda birikimli ve tek çeyrek tutarlar karıştırılmaz. TMS 29 parasal kazancı, sıradan yönetici ilişkisi, kilit denetim konusu, pay yüzdesi veya geçmiş tedbir tek başına yeni alarm sayılmaz. Finansal tablo eşitliği/satın alma gücü tutarsızlığı şirket riski yerine veri sorunu olarak gösterilir.

Genel sonuç: doğrudan dikkat gerekçesi veya en az iki farklı alanda işaret → `dikkat_gerektiriyor`; tek alanda → `sinirli_isaret`; gerekli veri yok → `yetersiz_veri`; yeterli incelenen finansal/piyasa verisinde işaret yok → `belirgin_isaret_yok`. Kapsam ve çalışma durumu bu sonuçtan ayrıdır; `partial + dikkat_gerektiriyor` mümkündür. Bu olasılık, dolandırıcılık hükmü veya al/sat emri değildir.

Codex yalnız kabul edilmiş belge paketlerini görür, internet araması kapalıdır. Sayısal hesap ve son sınıf Python'dadır. Türkçe iddia alıntıları, taraflar, tek işlem kapsamı, olumsuzluklar ve denetim ifadeleri kontrol edilir. Karşı beyanlar da saklanır; alıntı varlığı beyanın doğru olduğunu kanıtlamaz. Şirketin model eğitimindeki geçmişi silinemez, tam kör deney iddiası yoktur. Tahmin ve sahiplik adaylarında AI'ın sayı önerisi kaynak metindeki tam sayı/tarih/birimle eşleşmelidir; belirsiz adaylar reddedilir.

Aynı belge/prompt/model için doğrulanan AI cevabı yerel önbellekte tekrar kullanılır. Bir analiz ayardaki çağrı sınırına, bir replay toplam 128 yeni çağrıya tabidir. Bütçe biterse kalan kapsam eksik kaydedilir. İptal sonrası yeni aşama/ay başlatılmaz.

## Kayıtlar ve deney

`data/runs/RUN_ID/analysis.json`, `assessment.json`, `report.md`, `checkpoint.json` ve varsa `ai/` kayıtları oluşur. Türkçe sonuçlar PostgreSQL `bilanco.equity_results` tablosunda ayrı tutulur; mevcut Enron v1 tablolarına Türkçe yıllık/ara dönem tutarları doldurulmaz. Şema v3 önceki verileri silmez. Aynı run farklı sonuçla güncellenemez.

Geçmiş taramalar `data/replays/REPLAY_ID/replay.json` ve `replay.md` ile `bilanco.replays` tablosuna yazılır. Referans olaylar AI'ya verilmez:

- `pre-2025-spk`: 2024-09-30'dan 2025-03-31'e ay sonları + 2025-04-29. Referans 2025-04-30 SPK 2025/28.
- `pre-2026-funds`: 2025-05-31'den 2026-08-31'e ay sonları + 2026-09-16. Referans 2026-09-17 fon işlem kapanması. Şirket iflası etiketi değildir.

İlk göstergeden uyarı, bilinen düzenleyici kaynak içeren ilk snapshot, uyarıdan referansa gün, kapsam ve eksikler ayrı gösterilir. Bu aylık gözlemde ilk uyarıdır; gün içindeki ilk sinyal tarihi değildir. HATSN aynı yöntemle incelenebilir; 'temiz şirket' etiketi değildir. İnsan incelemesi/geniş şirket örneklemi tamamlanmadan tahmin başarısı yüzdesi verilmez. İlerleyen dönemdeki kaynak veya fiyatları değiştirmenin erken snapshot'ın hesap/sınıflarını etkilemediği sentetik testlerle kontrol edilir.

## 16 Ekim 2026 gerçek çalıştırma sonucu

Son kodla iki OZATD taraması çalıştırıldı; 25 tarih tamamlandı fakat kaynak kapsamı kısmi kaldı:

| Tarama | Tarih sayısı | Gerçek sonuç | Yerel replay kimliği |
|---|---:|---|---|
| pre-2025-spk | 8 | 8 yetersiz veri; göstergelerden dikkat/işaret yok | `fc6bfbfa-d41c-41be-b73d-aee19eb8a4f7` |
| pre-2026-funds | 17 | 10 yetersiz veri, 7 yalnız M01 sınırlı işaret | `dc2a5475-3704-4e44-9c77-4a63aaf87c31` |

İlk sınırlı işaret 2025-07-31; bu, 2025-04-30 tarihli SPK kararından **sonra**. İki taramada da `dikkat_gerektiriyor` üretilmedi; `lead_days` boş. 2026-09-16 son değerlendirmesi `b5550f11-6f4b-4139-95c8-f43c9a0a40fd`: yalnız piyasa kapsamı kullanılabilir, diğer dört alan verisiz. 60 işlem günlük getirinin endeksten ayrışması tek başına hile veya yaklaşan düşüş kanıtı değildir.

Bu ortamda KAP bağlantısı TLS `ConnectError` verdi; Yahoo fiyatları ve SPK PDF'si alınabildi. Finansal tablo/ilişki/denetim analizi gerçek KAP belgesiyle henüz doğrulanamadı. Bu yüzden sonuçlar **“Özata önceden yakalandı”** iddiasını desteklemiyor. Manuel belge paketi yolu var; bir sonraki gerçek doğrulama geçerli KAP PDF ve dipnot ekleriyle yapılmalı. HATSN için üç karşılaştırma tarihi de finansal veri eksikliği nedeniyle kısmi/yetersiz kaldı.

SPK belgesi için ilk taramada gerçek Codex çağrısı yapıldı; çıkarım prompt'u v2 olduktan sonra bir yeni çağrı daha yapıldı. Son iki tarama doğrulanan önbelleği kullandı, yeni AI çağrısı yapmadı. Eski SPK metni yalnız düzenleyici bağlamdır; şirket raporlarını incelemiş gibi alan kapsamı açılmaz.

196 otomatik test izole PostgreSQL ile geçti; Ruff kontrolleri temiz. Tarih sızıntısı, karşı örnekler ve kaynak hataları sentetik belgelerle sınandı. Bu sayı gerçek şirketlerde tahmin başarısı ölçümü değildir. Mevcut Enron analiz dosyasının SHA-256 değeri değişmedi.

## Bağlantı düzeldikten sonraki finansal koşu

16 Ekim 2026'da kullanıcının Sing-box servisi durdurulduktan sonra KAP PDF erişimi açıldı. Yukarıdaki25 kısmi tarama tarihsel kayıttır; otomatik olarak yeni finansal sonuca dönüşmedi. Yeni gerçek tek-tarih analizi **2025-03-31** için yapıldı.

Son düzeltilmiş koşu `04d1cc5b-9fd5-42e1-b760-733b0ef574a1`:93 kabul edilmiş belge,38 tutar,18 gösterge; sonuç `sinirli_isaret`, durum `partial`. F01 kâr–nakit ayrışması, F03 nakit/kısa finansal borç oranı uyarısı. Net kâr225.351.000 TL, faaliyet nakdi−1.173.912.255 TL, nakit/kısa finansal borç%12,19. İki işaret aynı alanda; `dikkat_gerektiriyor` koşulu sağlanmadı. Hasılat değişimi−%39,44; faaliyet marjı artışı nedeniyle O01'in ortak koşulu oluşmadı. Bu bulgular hile tespiti değildir.

Finansal/faaliyet sayısal kapsamı kullanılabilir; ilişkiler ve denetim için tam metin kapsamı yeterli sayılmadı.128 bulgunun126'sı bağlam.56 ret/çıkarım eksikliği, OCR ve ek kapsamı sorunları ile AI bütçesi açıkça korunur. Finansal yatırımların likiditesi nakit oranından çıkarılamaz; bu uyarının bilinmeyeni olarak gösterilir.

İlk geniş koşu `23defebb-1514-4515-8b6d-df5b81e30fef`32 yeni çağrı/1 önbellekle956,45 saniye sürdü. Belge türü düzeltmesi sonrası yeni koşu, aynı program fonksiyonuyla `max_ai_calls=0` kullanılarak33 doğrulanmış önbellek paketiyle34,81 saniyede yeniden hesaplandı. CLI en az1 yeni çağrı bütçesi kabul eder; bu cache-only yeniden hesaplama Python API'sindeki çalışma bütçesidir. Önbellekte olmayan metinler incelenmiş sayılmadı.

Gerçek veriyle bulunan okuyucu sorunu düzeltildi: belge türü, gövdedeki “finansal rapor/faaliyet raporu” ifadesinden değil kapak başlığından belirlenir. Kaynak edinimi ve AI sırası finansal raporları/faaliyet raporlarını önce, diğer açıklamaları güncelden eskiye işler. Yeni HTTP istekleri arasında en az2 saniye var; HTTP429 alınırsa aynı sunucuya bu koşuda yeni istek yapılmaz, sağlam önbellek ve diğer sunucular kullanılabilir. Eşikler değiştirilmedi.

[Çevrimdışı HTML](../demos/ozatd-2025-03-31.html) yalnız bu iki kayıtlı JSON'u görselleştirir; programın içine arayüz eklenmedi.200 test ve Ruff kontrolleri geçti. HTML'nin JSON/alıntı/filtre/indirme ve mobil/masaüstü kontrolleri de geçti. Sonraki görev, insan incelemesi ve daha geniş tarih/şirket örneklemi; başarı yüzdesi ölçülmüş değildir.

## Kaynak ve teknik araştırma

- [KAP resmî üretim REST erişim koşulları](https://www.kap.org.tr/tr/api/about/content-file/8a019492945fbe080194b26d8bed4873)
- [SPK 2025/28](https://spk.gov.tr/data/68126e9e8f95db0ba8ec02f2/2025-28.pdf)
- [SPK 2026 fon işlemleri açıklaması](https://www.spk.gov.tr/duyurular/basin-duyurulari/2026/tasfiye-suresine-iliskin-basin-duyurusu)
- [Yahoo fiyat düzeltme açıklaması](https://help.yahoo.com/kb/SLN28256.html)
- [trailingedge yazarının kamu sitesi endpoint gözlemleri](https://github.com/caganco/trailingedge/blob/master/docs/KAP_ENDPOINT_NOTES.md): deneysel web uçları; yazının erişim koşullarına ilişkin yorumları resmî izin veya SLA değildir.
- [Tradevo Data, tarih ve sürüm karışması](https://dev.to/tradevodata/your-backtest-saw-the-future-lookahead-bias-in-fundamental-data-measured-across-313562-rows-4cba): ticari ürün yazısı; yalnız yöntem uyarısı kullanıldı, performans iddiaları alınmadı.
