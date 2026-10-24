# Yatırımcı gözlemleri ve KERVN desteği

Güncelleme: 2026-10-18. Kural `tr-equity-review-3`, Analysis/Assessment `1.2`, AI istemi `tr-equity-extraction-4`. Bu sürüm, [v2](turkey-review-v2.md) üzerine eklenir. Enron'un kaynak, kural ve değerlendirme akışı değiştirilmedi. Eski JSON ve HTML dosyaları yeni kuralla çalıştırılmış sonuçlar değildir.

## Aynı akış

```text
analyze --company ozatd|hatsn|kervn --as-of TARİH
  → şirketin KAP kimliği ve kesime kadarki bildirimler
  → yayın zamanı + ihraççı + ek bağlantısı doğrulaması
  → tablo satırları ve muhasebe esası
  → Python ölçümleri
  → aynı kapalı belge paketlerinden AI'ın alıntılı olgu adayları
  → Python alıntı/taraf/tarih/ifade kontrolleri
  → aynı değerlendirme + 15 gözlemin kanıt ve eksik veri dökümü
  → PostgreSQL + analysis.json + assessment.json + report.md
```

Şirket adına göre risk formülü, vaka sonucu veya riskli kişiler listesi eklenmedi. KERVN için ayrıca model veya uygulama yok. Geliştirme sırasında KERVN risk verisi toplanmadı/analiz edilmedi; gerçek inceleme açık `analyze` komutuyla başlar. Örnek kullanım:

```sh
uv run bilanco analyze --company kervn --as-of 2016-03-31
```

Bu tarih yalnız komut örneğidir; olaydan tam bir yıl önce veya ilk düzenleyici açıklamadan önce olduğu iddia edilmez. KERVN'nin farklı SPK/dava olaylarından hangisinin test hedefi olduğu ayrıca belirlenmeli. OZATD'nin `pre-2025-spk` ve `pre-2026-funds` olay tarihleri KERVN'ye aktarılmaz; uyumsuz replay komutu veri/DB çalışması başlamadan reddedilir. KERVN, diğer hisseler gibi tarih kontrollü `--bundle ... --offline` akışını kullanır.

## Eklenen ölçümler

- **İlişkili taraftaki alacak:** kısa ve uzun vade ayrı; aynı vadedeki ilişkili ticari + diğer alacak / toplam varlık. İki bileşenden biri eksikse tam oran hesaplanmaz. Dash hücresi sıfır varsayılmaz. Vade/faiz/tahsilat bilinmeden gecikme veya kötüye kullanım denmez.
- **Tahsilat:** dönem başı ve sonu açıkça mevcutsa ortalama alacak / satış × gün. Bu fatura yaşlandırması veya şirketin açıkladığı gerçek tahsil süresi değildir. Eski dönem sonu alacak vekili ayrıca korunur.
- **Kâr/nakit kalıcılığı:** aynı son raporda karşılaştırılabilir en az iki tam yıl varsa pozitif kâr + negatif faaliyet nakdi görülen yıl sayısı. Çeyrekler üst üste toplanmaz; aynı dönem iki kere sayılmaz. Tek başına kalıcılık/bozukluk hükmü değildir.
- **Stok:** gerçek dönem başı ve sonu / satış maliyeti × dönem gün sayısı; başlangıç bakiyesi yoksa ortalama tahmin edilmez. Stok büyümesi ile karşılaştırılabilir satış büyümesi farkı ayrıca gösterilir.
- **Sözleşme varlığı:** kısa/uzun vade ayrı, dönem hasılatına oran. Ticari alacakla birleştirilmez.
- **Kâr bileşenleri:** faaliyet kârı ve yatırım gelirinin pozitif vergi öncesi kâra oranı; TMS29 oranı korunur. Bunlar 'düzeltilmiş kâr' veya sahte kâr hesabı değildir.
- **Nakit köprüsü:** yatırım/finansman bağlantılı belirli mutabakat satırı açıkça çıkarılabiliyorsa faaliyet nakdi içindeki büyüklüğü ve satır hariç aritmetik duyarlılık. Duyarlılık **doğrulanmış/düzeltilmiş OCF değildir**. Negatif satırın büyüklüğü negatif OCF'nin en az yarısıysa F01 genel risk oyundan bağlama indirilir; kaynak açıklaması korunur. Bu %50 koşulu yorum korumasıdır, ampirik tahmin eşiği değildir. Borç/likidite kontrolü ayrıca kalır.

Tüm tutarlar, aynı bildirim/bağlı ek, para birimi, dönem, konsolidasyon kapsamı, raporlama esası ve baz tarihiyle eşleşir. Nominal tutarlar reel büyüme olarak sunulmaz. Yeni ölçümlerin büyüklüğünden tek başına şirket alarmı üretilmez.

## On beş gözlem

| Alan | Kod / veri yolu |
|---|---|
| Kâr–nakit–tahsilat | Hesaplar + `cash_collection` kaynak beyanı |
| Ortak/ilişkili alacak | Hesaplar + `related_receivables` vade/tahsil beyanı |
| İlişkili varlık/kira/teminat şartı | Mevcut `observations` + `related_terms` |
| Yakın borç/serbest kaynak | Mevcut nakit/borç hesabı + `liquidity` |
| Kâr bileşenleri | Hesaplar + `earnings_quality` |
| İş/hedef gerçekleşmesi | Mevcut aynı bazlı tahmin karşılaştırması + `execution` |
| Halka arz/bedelli kullanımı | `proceeds_use`; plan değişikliği/geçici yatırım karşı açıklamaları |
| Belirli denetim sorunu | Mevcut görüş kontrolleri + `audit_specific` |
| Belge tutarsızlığı | `report_consistency`; düzeltme/sürüm/aynı taraf bağlamı |
| Ortak satışı ve olumlu anlatı | `insider_sales`; ikisi aynı dönemde açıkça kanıtlı olmalı |
| Fiyat/operasyon ayrışması | Mevcut günlük getiri/endeks/hacim + `price_operations`; sektör emsali eksik kalabilir |
| Çıkış/yoğunlaşma | `exit_concentration` kaynak beyanı; gerçek derinlik/saklama entegrasyonu yok |
| Kapanış davranışı | `closing_pattern` kaynak beyanı; gün içi veri hattı bağlı değil |
| Büyük emir iptali | `order_cancellations` kaynak beyanı; emir olay veri hattı bağlı değil |
| Stok/sözleşme dönüşümü | Hesaplar + `inventory_contracts` |

Son üç piyasa başlığını günlük kapanıştan hesaplıyormuş gibi sunmuyoruz. Kaynak bu davranışı açıkça raporlayabilir; bu da bağımsız emir analizi değildir. Fonun şirkette pay sahibi olması ile şirketin fona yatırım yapması farklı yönlü ilişkilerdir. Nihai tek kişi/koordinasyon sonucuna gidilmez.

## AI ile Python'un ayrımı

`analysis.signals`, her aday için tür, ihraççı, kaynakta geçen konu/varlık/karşı taraf, açık dönem/olay tarihi, `issue/counterstatement/unknown`, beyan türü ve blok/alıntı taşır. AI fiyat veya matematik hesaplamaz, serbest risk kararı vermez.

Python, alıntının verilen blokta olduğunu; ihraççıyı, konuyu ve tarihleri; konuya özgü açık sorun ifadesini kontrol eder. Yalanlanan/olumsuzlanan ifadeler ve genel denetim sorumluluğu metni sorun diye kabul edilmez. Bunlar tam semantik doğrulama değildir. Karşı açıklamalar atılmaz. Gelecek tarih, bulunmayan taraf, uydurma alıntı ve yargı bilgisinin doğrudan şirket olgusu gibi etiketlenmesi ret nedeni olur; aday JSON'u korunur.

Yeni S-* kayıtları, uygun kaynak ve açık tarihli somut beyan varsa **inceleme adayı** olabilir. **Kalibrasyon yapılana kadar genel şirket sonucuna oy vermezler**; bu politika AI'a bırakılamaz. Dava/iddia ve bilinen mahkeme/SPK kararı bağlamdır; yeni göstergeden önceden tahmin diye sayılmaz. Dava ile mahkûmiyet/kesinleşme ayrılır. Aynı riskin birden çok ölçümü bağımsız oy diye çoğaltılmaz.

`assessment.signal_checks` her gözlemi üç durumdan biriyle gösterir:

- `evidence_found`: ilgili kaynaklı kayıt var; mutlaka olumsuzluk değildir.
- `partial`: bir ölçüm var, bütün mekanizma değerlendirilemedi.
- `unavailable`: yeterli doğrulanmış girdi yok; 'işaret yok' demek değildir.

Her kaydın bulgu/gösterge kimlikleri ve eksik girdileri vardır. `report.md` aynı listeyi okunabilir tabloda verir. Ana dosya yolları ve DB JSON saklama akışı değişmez; yeni DB servisi/migrasyon gerekmez. Eski 1.0/1.1 kayıtları okunabilir, eski dosyalar yeniden yazılmaz.

## KERVN ve geçmiş raporlar

KAP'ta [şirket kimliği](https://www.kap.org.tr/tr/sirket-bilgileri/ozet/897-kervansaray-yatirim-holding-a-s) ve [aracı kurumda ilk işlem tarihi](https://oyakyatirim.com.tr/hisse-detay/KERVN) kontrol edildi. Üye OID'si tahmin edilmedi: program açıldığında mevcut KAP `attachment-detail/1487889` kimlik kaydından yalnız şirket adı/kodu/üye kimliği eşleştirilir. Bu sonraki tarihli yönlendirme kaydının rapor metni/ekleri geçmiş analiz veya AI paketi olmaz; cache'teki ham metadata risk kanıtı sayılmaz. Üye kimliği doğrulanamazsa hata açıkça kalır; başka şirkete sorgu yapılmaz. Canlı KERVN edinimi henüz doğrulanmadı.

Katalog, uzun süredir işlem gören şirketlerde varsayılan **1096 günlük** pencereyle sınırlıdır; daha eski belgelerin taranmadığı rapora yazılır. Yeni metadata veya katalog belgesi, geçmişte o gün arşivlenmiş baytların bağımsız kanıtı değildir. Eski CEYLN unvan/kod dönemleri otomatik birleştirilmez; doğrulanmayan kimlik kaynak olarak alınmaz.

Eski nominal rapor için açık nominal/enflasyon uygulamasına son verme beyanı, tarihli başlık, kapsam ve birim aranır. Yalnız '2016' yazdığı için nominal varsayılmaz. Yeni raporların TMS29 şartı gevşetilmedi. Nominal ve enflasyona göre düzeltilmiş veriler karşılaştırılırsa sonuç veri sorunu olur. Farklı solo/konsolide ve yıl/çeyrek sütunlar karıştırılmaz. OCR hâlâ bağlı değildir; görüntü ekinin okunamaması açık eksikliktir.

## Doğrulama kapsamı

Yeni testler tamamen yapaydır; gerçek KERVN veya Enron başarısı değildir. Alıntı/tarih/ihraççı sahteciliği, normal işlem ve olumsuzlama, mahkeme bilgisinin geçmişe sızması, nominal muhasebe, vade ayrımı, stok başlangıç bakiyesi ve aynı CLI/JSON/DB akışı sınanır. Canlı veri erişimi ve yeni AI isteminin gerçek şirketlerde kalibrasyonu ayrıca yapılmalıdır. Bağlantı engelleri aşılmadı, TLS kapatılmadı, Sing-box ayarı değiştirilmedi.

Mühendislik kontrolünde [Michael Maurice'in şema/alıntı doğrulama yazısı ve yorumları](https://dev.to/michael_maurice/schema-valid-correct-4-checks-before-you-trust-llm-extraction-4n6f) ile [Alex Merced'in veri kalitesi yazısı](https://dev.to/alexmercedcoder/data-quality-is-a-pipeline-problem-not-a-dashboard-problem-48fd) okundu. Bunlar finansal kuralların ampirik doğrulaması değildir; geçersiz adayın neden/konumuyla saklanması ve eksik bilginin sıfır yapılmaması yaklaşımıyla ilgilidir.
