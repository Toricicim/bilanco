# Kaynaklı erken inceleme — v4

Güncelleme: 23 Ekim 2026. `tr-equity-review-4`, Analysis/Assessment `1.3`, AI istemi `tr-equity-extraction-5`. Önceki [15 gözlem](investor-checks.md) ve Enron akışı korunur. Bu sürüm gerçek şirketlerde doğrulanmış dolandırıcılık tahmin başarısı sunmaz.

## Ne değişti?

```text
analyze --company ... --as-of ...
  → kesimden önce yayımlanmış KAP belgeleri ve bağlı ekler
  → Python tablo çıkarımı + mevcut kurallar
  → aynı kapalı belge paketinden AI'ın nötr taraf/tutar/tarih adayları
  → Python alıntı, sayı, dönem, kapsam, kaynak ve yön kontrolleri
  → plan/gerçekleşme ve sözleşme tarafı karşılaştırmaları
  → şirket → fon maruziyeti, kaynak varsa tarihli fon toplamı/iade şartı
  → kaynak sürümleri korunarak dönemli kâr/nakit geçmişi
  → genel sonuç + ayrı yatırım öncesi inceleme mesajı + kontrol izleri
  → PostgreSQL / analysis.json / assessment.json / report.md
```

Kurallar şirket adına veya bilinen sonuca göre değişmez. Özata için yeni finansal sayı/olay sonucu veya `triggered: true` profili eklenmedi. Sonraki olayları AI paketine ekleyen keşif yapılmaz. Hiçbir yeni arayüz/HTML yoktur.

## Nötr olgular ve karşılaştırma

AI `document_facts` içinde `proceeds_plan`, `proceeds_spent`, `contract_owner`, `fund_position`, `fund_net_assets`, `fund_redemption_days` çıkarabilir. Şirketin kaynakta "bir sorun var" demesi gerekmez. Bunlar AI'ın yatırım yorumu değildir. Her olguda taraf/konu, tarih, tutar ve konumlu alıntı bulunur. Tutar kopyalanır, hesap Python'dadır.

- Plan/gerçekleşme yalnız aynı proje, dönem başlangıç/bitişi, para birimi, kapsam ve muhasebe bazında, en az iki farklı kaynakla karşılaştırılır. Plan dönem bitiminden önce kamuya açıklanmış olmalıdır. Dokuz ay/yıllık karışımı hesap üretmez. Basılı sayıların hassasiyetinden yuvarlama toleransı hesaplanır; ampirik risk eşiği değildir.
- Fark bulunması `D-proceeds` inceleme adayıdır. Harcamanın düşük/yüksek olması otomatik amaç dışı kullanım değildir. Aynı projeye ait açık plan güncellemesi/onay beyanı karşı alıntıda varsa fark bağlamda kalır. Varsayımsal veya başka projeye ait açıklama bunu bastırmaz.
- Aynı sözleşme/dönem iki kaynakta farklı tüzel kişiye atfedilmişse `D-contract_party` adayı oluşur. Devir/düzeltme veya yanlış veri çıkarımı olabilir; gelir hangi şirkete ait diye sorulur. Üst şirketin işi otomatik listedeki şirkete yazılmaz.
- Sadece sayının belgede bulunması yeterli değildir: etiketli `value_evidence` satırı, tarih, para birimi/kapsam ve kaynak rolü kontrol edilir. Bin/milyon/milyar veya yüzde satırı tahminle dönüştürülmez. Birden çok hücre varsa tutar ancak açık sıralı tarih başlığıyla dönem sütununa bağlanır. Liste tiresi sayı, eksik karşılaştırma hücresi sıfır sayılmaz; başlıksız veya yanlış dönemli satır reddedilir. Eski Python tablo okuyucusu ayrı olarak ölçekli finansal tabloları okuyabilir.
- Bu metin kontrolleri tam anlam doğrulaması değildir. Model yanlış ilişki/alan seçebilir; alıntıların insan tarafından örneklenerek kontrolü gerekir. Ret nedeni ve ilk aday saklanır.

## Fon belgesi nasıl eklenir?

Fon kodu, şirketin finansal yatırımının yönünü gösteren bir alıntıyla çıkarılır. Fonun şirket hissesi alımı, şirketin fon alımı gibi kabul edilmez. Aynı tarih/baz/kapsam varsa pozisyon / şirket toplam varlıkları hesaplanır. Tarihli fon toplamı da varsa pozisyon / fon toplam değeri hesaplanabilir; bu **değerleme maruziyeti vekilidir, teyit edilmiş pay sahipliği veya kontrol değildir**.

Güncelleme23Ekim2026: Türkiye analyze için [sınırlı otomatik KAP kaynak keşfi](source-discovery-routing.md) eklendi; bütün fonların/arşivlerin keşfi garanti edilmez. Aşağıdaki manuel paket yolu ayrıca desteklenir. Fon belge kimliği paket manifestinde açık kaynak yönlendirmesi olarak verilebilir. Aşağıdaki değerler **yalnız yapısal örnektir; gerçek kod/ad/kimliklerle değiştirilmelidir**:

```json
{
  "company": "ozatd",
  "documents": [{"disclosure_id": 123456788, "file": "sirket-kap.pdf"}],
  "related_documents": [{
    "fund_code": "ABC",
    "fund_name": "ÖRNEK PORTFÖY ÖRNEK FON",
    "disclosure_id": 123456789,
    "file": "fon-kap.pdf"
  }]
}
```

Fonun kodu ve adı **önce şirketin kabul edilmiş belge bloğunda birlikte bulunmalı**. Ardından fonun kendi KAP PDF'sindeki ad, kalıcı bildirim kimliği ve yayın zamanı doğrulanır. Manifestten yayın tarihi veya finansal tutar kabul edilmez. Kesimden sonraki fon belgesi reddedilir. Fon belgesi şirketin finansal tablosu veya yönetici ilişkisi sayılmaz.

`file` verilmezse, çevrimiçi paket koşusunda belirtilen KAP PDF kimliği çalışma sırasında indirilir. `--offline` kullanılırsa dosya gerekir. Ekler için aynı `detail_file`/`attachments` kanıt sözleşmesi geçerlidir. En çok 20 ilişkili belge yönlendirmesi kabul edilir. Paket modunun ana şirket belgeleri de aynı paketten gelir; bu seçenek canlı şirket taramasına otomatik fon araması eklemez.

Fon iadesi için tarihli koşul ve açık iş günü/takvim günü ayrımı aranır. İade günü bile tek başına pozisyonun kesin o sürede nakde döneceğini kanıtlamaz. Alt varlıklar, blokaj, tam portföy ve borç vadeleri eksikse eksik kalır; fon nakitle eşitlenmez. Genel ve çok katmanlı fon-ağ keşfi, fiyat etkisi ve gerçek emir/saklama entegrasyonu bu sürümde tamamlanmış değildir.

## Çıktıyı okuma

`analysis.json` yeni alanları:

- `document_facts`: kabul edilen kaynaklı nötr adaylar; `document_fact_index` hesap/karşılaştırma kimliklerini bu kayıtlara bağlar.
- `comparisons`: fark, tutarlılık, bağlam veya karşılaştırılamama; kullanılan girdi ve gösterge kimlikleri.
- `fund_exposures`: şirket → fon yönü, bağlı kaynaklar, oranlar, iade günü/türü, eksikler.
- `financial_history`: ilk kullanılabilir uyumlu raporlardan dönemli kâr/nakit oranı. Birikimli çeyrekler toplanmaz, farklı satın alma gücü seviyeleri birbirine eklenmez. Yeterli 8–12 çeyrek veya sektör emsali her şirket için mevcutmuş gibi sunulmaz.

`assessment.json` yeni alanları:

- `check_traces`: eski 15 gözlem + belge karşılaştırması, fon/likidite ve geçmiş için 18 iz. Kaynak havuzu/taranan kaynak, kabul/ret, ret nedenleri, hesaplanan göstergeler, bulgular ve eksikler görünür. Kaynak tarandı demek bütün ekonomik girdiler bulundu demek değildir.
- `investor_review`: `inceleme_gerekli`, `veri_yetersiz` veya `belirgin_ek_isaret_yok`. Kaynaklı `review/critical` adayları, genel sonuca oy vermeseler de burada görünür. İlk mesaj yatırım öncesi inceleme çağrısıdır; al/sat emri veya suç hükmü değildir.

Eski `outcome` pilot politikası ayrı durur. Örneğin genel sonuç sınırlı kalırken yeni belge farkı inceleme kuyruğuna girebilir. Bu ayrım başarı kanıtı değildir; iki çıktının yanlış alarmı ayrı ölçülmelidir. Yeni adayların hepsini genel alarma saymak veya F01'in bağlam kuralını Özata alarm versin diye gevşetmek yapılmadı. Nakit köprüsünün %50 ve alan sayısı kuralları ampirik doğrulanmış değildir.

Terminal JSON'u ve `report.md` yeni mesajı gösterir. Dosyalar her zamanki `data/runs/<RUN_ID>/` altındadır. PostgreSQL JSON kaydı aynı tabloyu kullanır; yeni DB servisi veya migrasyon gerekmez. Eski 1.0/1.1/1.2 kayıtları okunabilir; eski snapshot dosyaları yeniden yazılmaz ve yeni sonuçmuş gibi sunulmaz.

```sh
uv run bilanco analyze --company ozatd --as-of 2025-03-31
uv run bilanco analyze --company kervn --as-of 2016-03-31
# Kaynak yönlendirmeleri ve tarihli dosyalar varsa:
uv run bilanco analyze --company ozatd --as-of 2025-03-31 --bundle ./belgeler --offline
```

Bu komutlar gerçek analiz başlatır. KERVN tarihi yalnız kullanım örneğidir, bağımsız olay protokolü değildir. Şirket etiketi veya bilinen olay, analiz girdisi olmaz.

## Yanlış alarmı ve kaçırılan vakaları ölçmek

`evaluate-study` yalnız **önceden üretilmiş** Analysis/Assessment dosyalarını okur. Finansal HTTP, model ve PostgreSQL kullanmaz. Etiketli manifesti analiz/AI çağrısına göndermez.

```sh
uv run bilanco evaluate-study --manifest ./deney/study.json --output ./deney/sonuc-v4.json
```

Manifest örneği aşağıda; hedef tanımı ve etiket kaynağı araştırmacı tarafından doğrulanmalıdır. Gerçek araştırma sonucu değildir:

```json
{
  "schema_version": "1.0",
  "target_definition": "Belirli türdeki ilk kamuya açıklanmış olayın sonraki 365 günde görülmesi",
  "horizon_days": 365,
  "rule_version": "tr-equity-review-4",
  "development_company_ids": ["ozatd", "kervn"],
  "cases": [{
    "company_id": "hatsn",
    "split": "test",
    "analysis": "hatsn/analysis.json",
    "assessment": "hatsn/assessment.json",
    "target_event_observed": false,
    "event_date": null,
    "followup_end": "2026-04-01",
    "label_source": "ÖRNEK: belirlenen takip penceresini kapsayan araştırmacı kaydı"
  }]
}
```

Bu örnek HATSN'nin temiz olduğunu iddia etmez; gerçek etiket/snapshot gerekir. Yollar manifest klasörünün içinde kalmalıdır. Çıktı dosyası varsa üzerine yazılmaz. Analiz hash'i, koşu/şirket/tarih/kural sürümü ve kaynak/fiyat kesimi doğrulanır. Olay analizden sonra, belirlenen pencerede olmalıdır. Kontrol için tam takip penceresi gerekir; olay yaşamamış demek kesin masum demek değildir.

Bir şirket aynı deneyde tek kez sayılır. Geliştirmede görüldüğü beyan edilen şirket test listesine giremez. Özata artık bağımsız test vakası değildir. Bu beyan kontrolü, insanın/modelin önceki bilgisini silemez. Şirket dışarıda tutma ve zaman ayrımı araştırmacının sorumluluğudur.

İki çıktı için ayrı yakalama, yanlış alarm, örneklem alarm isabeti ve uyarının olaya uzaklığı verilir. `yetersiz_veri`/`veri_yetersiz` ve başarısız sonuçlar güvenli kabul edilmez; çekimser sayısı ayrıca gösterilir. Yakalama paydasında kaçırılan/verisiz olay şirketleri korunur. Yanlış alarm oranı değerlendirilebilen kontroller üzerinde, kapsamıyla birlikte verilir. Eşlenmiş küçük örneklemin alarm isabeti gerçek piyasa sıklığına doğrudan genellenemez.

## Doğrulama ve kalan işler

23 Ekim'de **335 test**, izole gerçek PostgreSQL'deki 6 test dahil geçti. Yeni 52 test durumu yapay kaynak/etiket kullanır. Gerçek finansal HTTP ve gerçek model çağrısı testlerde yoktur. Tarih sızıntısı, yanlış şirket/kod, uyumsuz dönem/baz, yanlış tutar, ölçek belirsizliği, plan güncellemesi, hash değişikliği ve geliştirme/test karışması sınandı. Bu sayı tahmin başarısı değildir.

Yeni sürümle sınırlı bütçeli gerçek Özata kontrolü yapıldı; tam kaynak taraması veya tahmin başarısı değildir. Gerçek KERVN koşusu, OCR, otomatik çok katmanlı fon kaynak keşfi, sektör/likidite emsali, gerçek emir/saklama verisi ve şirketlerde kalibrasyon açık işlerdir. Eski gerçek JSON/HTML yeni sürümün çıktısı sayılmaz; güncellenen demonun koşusu demos/README.md içinde belirtilir.

Mühendislik kontrolünde [Michael Maurice'in şema/kanıt yazısı ve yorumları](https://dev.to/michael_maurice/schema-valid-correct-4-checks-before-you-trust-llm-extraction-4n6f) ile [Tradevo Data'nın tarihli test yazısı ve yorumları](https://dev.to/tradevodata/how-to-backtest-value-investing-without-lookahead-bias-3b0a) okundu. Kaynak konumu ve yayın/sürüm kontrolleri için kullanıldı; bağımsız finansal performans kanıtı değildir.

Codex bağlantısında, Pydantic varsayılanlı alanların strict çıktı şemasında required listesine girmemesi nedeniyle gerçek çağrıların reddedildiği doğrulandı. Wire şeması bütün object alanlarını required ve additionalProperties=false yapar; nullable anlamları ve domain doğrulaması korunur. Şema hash'i receipt'e yazılır; üst düzey hata ayrıntısı sırlar/URL'ler maskelenerek saklanır. Basit ve genişletilmiş şema gerçek yapay bağlantı çağrısıyla doğrulandı. [Resmî strict şema şartları](https://developers.openai.com/api/docs/guides/function-calling#strict-mode).

## 23 Ekim sınırlı gerçek kontrolü

Güncel demo koşusu `e3929681-ce54-48c1-a725-45c6ffeaacf3`, 31 Mart 2025 kesimi:94 belge/148 tutar/29 gösterge/6 geçmiş dönem. Önce iki koşuda9 gerçek başarılı AI yanıtı alındı; nihai yeniden doğrulama0HTTP/0yeniAI,9doğrulanan önbellek ile yapıldı.141planlı paketin9'u işlendi; sonuç partial/sinirli_isaret, inceleme mesajı inceleme_gerekli. F01/F03 dışında yeni genel risk oyu yok. IBG/PPZ kaynaklı pozisyonları iki nötr olgu/fon izi olarak çıktı; ilgili fon belgeleri, iade ve kapsam eşlemesi eksik kaldığından daha ileri oran/likidite sonucu üretilmedi. Belge karşılaştırma çifti oluşmadı. Bu kapsamlı erken yakalama başarısı değildir.
