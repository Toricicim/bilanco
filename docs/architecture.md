# V1 mimari sözleşmesi

Güncelleme: 2026-10-16. Grafik/HTML/HTTP API/daemon analiz hattının parçası değildir. Tamamlanmış bir koşunun ayrı HTML gösterimi `demos/` altındadır.

## Ek değerlendirme katmanı

`assess --run-id` kayıtlı Analysis v1'i değiştirmeden yönetici/ilişkili işlem adaylarını değerlendirir. Yeni `analyze` komutları aynı adımı otomatik çağırır. AI alıntılı alt soruları cevaplar; Python kaynak denetimi, öncelik kuralı, tekrarları birleştirme ve sıralamayı uygular. Assessment v1, ayrı `data/assessments/<id>/` dosyaları ve şema sürümü 2'deki `assessments` tablosuna yazılır. Eski Analysis şeması korunur. [Tam sözleşme ve sınırlar](assessment.md).

## Parçalar ve sınırlar

| Katman | Sorumluluk | Yapmadığı iş |
|---|---|---|
| CLI | Girdi doğrulama, açık çalıştırma, ilerleme, çıkış kodu | Otomatik zamanlanmış finansal veri toplama |
| Acquirer | Sınırlı HTTPS, SEC kimliği, retry, hash, ham önbellek | Erişim engeli aşma, AI tarihini doğru kabul etme |
| Belge okuyucu | Ana belge, sayfa/blok/satır, tablo sütunu, birim | Eksik tutarı tahmin etme, OCR modeli indirme |
| Python hesapları | Kesin ondalık aritmetik, formüller ve basit kurallar | Çöküş/dolandırıcılık olasılığı atama |
| Codex keşif | En fazla beş kaynak URL'si | Finansal bilgiyi arama özetinden veri tabanına yazma |
| Codex çıkarım | Kaynak pasajından sınırlı türde adaylar | Yeni sayı/isim üretip kesinleştirme |
| Kontrol | Alıntı/blok/aktör eşleşmesi, ret ve inceleme durumu | Otomatik anlam ispatı |
| Codex sunum | Var olan bulgu kimliklerinin sırası | Yeni olgu veya serbest sonuç paragrafı |
| Depo | Kalıcı kaynak, dönemli sayısal alanlar, çalışmanın tam kaydı | Ham PDF'yi JSONB'ye dönüştürüp byte aslını kaybetme |

## Veri akışı

1. `Settings.load()` yalnız mevcut dizinin `.env` dosyasını okur.
2. `analyze` şirket/tarihi/SEC iletişim alanını kontrol eder. Şema hazırlanır, benzersiz çalışma başlar.
3. Özgün SEC raporu çalışma sırasında alınır; gerekirse SEC yayın kanıtıyla ilişkilendirilmiş arşiv PDF'si denenir. Keşif ayrı bir yeni Codex çağrısıdır. Modelin sunduğu URL tekrar indirilir ve kodla tarih/kimlik kontrolünden geçer.
4. Kabul edilen belgelerden bütün metin blokları okunur. Ana finansal tablolardaki tutarlar programatik çıkarılır. Notlar sayısal tablo satırı gibi ele alınmaz.
5. Okunabilen bütün bloklar boyut sınırlı paketlerle AI aday çıkarımına gider. Paket sayısı ve incelenen paket sayısı kaydedilir. Çağrı bütçesi veya hata yüzünden eksik kalan paketler açıkça görünür.
6. Sayısal bulgularla AI inceleme adayları ayrı statülerde birleştirilir; anlatıcı yalnız kimlikleri sıralar. Eksik sıralanan kimlikler kaybolmaz.
7. Dosyalar geçici yazım + atomik yeniden adlandırmayla, PostgreSQL kayıtları tek transaction ile tamamlanır. Yeni çalışma eskisinin dosyalarını değiştirmez.

## Veri sözleşmesi

`analysis.json` şema sürümü `1.0`: `run_id`, `company`, `as_of`, `status`, `sources`, `blocks`, `facts`, `metrics`, `findings`, `rejected`, `limitations`, `ai`, `timings`, `overall`.

- **Source:** özgün/son URL, SHA-256, ham dosya yolu, edinim zamanı, yayın tarihi ve kanıtı, asıl/arşiv ayrımı, önbellek kullanımı.
- **Fact:** kavram, dönem, basılı ondalık değer, ölçek, birim, tutar/yıl/birim/para bağlamı kaynak konumları. Sütun ilişkisi belirsizse kabul edilmez. Aynı kavram/dönem için çelişen değerlerden biri keyfî seçilmez.
- **Metric:** Python hesabı, formül ve girdi fact kimlikleri. Eksik veri veya sıfır/uygunsuz payda hesap üretmez.
- **Finding:** sayısal işaret, bağlam veya ayrı `needs_review` adayı; kaynak/fact kimlikleri. Hile olasılığı veya kişisel yatırım önerisi değildir.
- **AI receipt:** görev, prompt sürümü, girdi hash'i, istenen model/CLI varsayılanı, izin profili, olay türleri, varsa token kullanımı ve süre. CLI varsayılanının gerçek model sürümü elde edilememişse sürüm doğrulandı diye yazılmaz.

PostgreSQL'de `runs`, `downloads`, `sources`, `run_sources`, `blocks`, `facts`, `metrics`, `findings`, `migrations` tabloları vardır. Parasal ham değer `numeric`, ölçek ayrı sütundur; JSONB kaynaklı ek yapıyı korur. Ham dosyalar hash üzerinden isimlendirilir.

## Kural kapsamı

- Cari oran: dönen varlıklar / kısa vadeli yükümlülükler. 1 altı inceleme işareti; 1 üstü güvenli yatırım hükmü değildir.
- Nakit / kısa vadeli yükümlülük ve uzun vadeli borç / özkaynak: bağlam olarak raporlanır; sektörler arası ortak eşik varsayılmaz.
- Net kâr pozitifken faaliyet nakdi pozitif değilse inceleme işareti.
- Kâr artıp faaliyet nakdi düşüyorsa ayrışma işareti; nakdin negatif olduğu iddia edilmez.
- Varsa bilanço eşitliği kontrolü: uyumsuzlukta değerler düzeltilmez, veri incelemesi gerekir.
- İlişkili işlem, yönetici–karşı taraf, kredi koşulu, garanti ve denetim alıntıları: AI adaylarıdır. Garanti tutarları borçla veya birbirleriyle otomatik toplanmaz.

Gelecekte doğrulanmış eğitim/etiketli değerlendirme seti oluşturulmadan bu kuralların risk tespit başarısı yüzdesi ilan edilmeyecek. Şu anki testler mühendislik doğruluğunu ölçer.

## Hata ve tekrar çalıştırma

- İndirmede HTTP 429/uygun 5xx en fazla üç deneme; 403 engeli aşılmaz. Yönlendirmede de alan adı kontrolü uygulanır. Sıkıştırması açılmış içerik için boyut sınırı vardır.
- Tarihi belirsiz kaynak hesap girdisi olmaz. PDF arşiv eşdeğerliği tam doğrulanamıyorsa çalışma kısmi kalır.
- Model hatası sayısal sonuçları silmez. Bilinmeyen şema/araç olayı yanıtı reddettirir; sonsuz AI düzeltme döngüsü yoktur.
- Kesilmiş süreçte sağlam indirmeler saklanır. Yeni analiz yeni çalışma kimliğiyle başlar; önceki incomplete çıktı başarı diye yeniden etiketlenmez.
- Tamamlanmamış çalışmada önbellek veri toplama hatalarını azaltır; önceki AI çağrılarının kaldığı yerden otomatik sürdürülmesi bu sürümde yoktur.
- Çalışma süreleri hız darboğazını ölçmek içindir. Rust'a geçiş veya eşzamanlı çoklu worker eklemek ölçüm sonrasına bırakılmıştır.
- `document_reading` ve `http_requests` alt ölçümlerdir; ana aşamalarla örtüştükleri için bütün süre alanları toplanarak toplam süre bulunmaz.
