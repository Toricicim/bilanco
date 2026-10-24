# Kayıtlı koşular — HTML gösterimleri

Güncelleme: 2026-10-23.

[enron-run-88f8d197.html](enron-run-88f8d197.html) dosyasını indirip tarayıcıda açın. Tek başına paylaşılabilir; sunucu, veritabanı, API anahtarı veya internet bağlantısı gerektirmez.

- Kaynak çalışma: `88f8d197-9734-480e-9b46-3d374d963b1b` / Enron Corp. / bilgi kesimi `2000-03-31`.
- Ek değerlendirme: `45f3f642-ee3c-4eb9-9485-010289eae8c7`, kural sürümü `related-party-1`. LJM yönetici bağlantılı işlemi öncelikli incelemeye çıktı.
- Kayıtlı `analysis.json` ve `assessment.json` dosyalarının tamamı HTML içinde gömülüdür. İki JSON indirme düğmesi özgün veri yapılarını ayrı ayrı dışa aktarır; özetler ve dosya hash değerleri gösterilir.
- Üst bölümde 1 öncelikli, 15 ek inceleme, 37 bağlam ve 7 değerlendirilemeyen konu; ilk üç konu ve LJM için yönetici bağlantısı/işlem/aynı taraf alt cevapları gösterilir. Bütün 60 konu, gerekçeler, bilinmeyenler, destekleyen ve dengeleyici alıntılar aranıp önceliğe göre filtrelenebilir.
- Değerlendirmede 70 adayın 68’i kontrollerden geçti; şirket ve taraf eşleşmesi nedeniyle iki aday reddedildiği için durum `partial`. Adaylar birleştirildiği için konu sayısı farklıdır. Kaynak analizin kısmi durumu ve kapsam dışındaki 54 AI adayı ayrıca belirtilir.
- İlk analizin bütün 133 bulgusu, 10 göstergesi, 19 sayısal verisi ve sınırları korunur. Yeni risk puanı, eşik veya finansal yorum eklenmez. İnsan incelemesi yapılmış sayılmaz; yönetim beyanı bağımsız doğrulama olarak gösterilmez.
- Grafikler yalnız kayıtlı oranları/yüzde değişimlerini gösterir. Ekranda yuvarlanan sayıların tam hassasiyeti gömülü JSON'da korunur.
- İki bölümün arama, filtre, sayfalama ve kaynak alıntıları çevrimdışı çalışır. Yazdırmada seçili filtrelere uyan bütün kayıtlar açılır. Özgün SEC bağlantısına tıklamak internet gerektirir.
- Bu, tamamlanmış koşunun sabit görsel çıktısıdır; uygulamanın analiz hattına arayüz veya yeni veri toplama adımı eklenmedi.

Not (2026-10-16): Bu dosya related-party-1 koşusunun tarihsel snapshot’ıdır. Kod daha sonra related-party-2 ile düzeltildi; eski JSON/HTML sessizce değiştirilmedi. Yeni kural çıktısı için yeni assess çalışması gerekir.


## Özata Denizcilik — 31 Mart 2025

Güncelleme: 2026-10-24.

[ozatd-2025-03-31.html](ozatd-2025-03-31.html) güncel 70 paketlik çıktıyı gösterir. Tek dosyadır; sunucu, API anahtarı veya veritabanı olmadan paylaşılabilir. Kaynak bağlantıları dışında çevrimdışı çalışır.

- Kaynak koşu: `769a301b-a401-42a4-a74a-db7b922aa96a`; kesim 2025-03-31 İstanbul gün sonu. Kural `tr-equity-review-4`, şema 1.3, çıkarım 5. Önceki `450216f0-d9ff-4839-bc50-973b08cb448b` koşusunun tarihli kaynakları ve ham dosya hash'leri doğrulanarak yeni UUID ile kullanıldı.
- **70/141 paket işlendi**, 71 paket sınır nedeniyle okunmadı. İşlenen 70 paketin 30'unda reddedilen adaylar var; işlenmiş paket bütün iddiaları onaylanmış paket değildir. Durum **partial**.
- Genel sonuç **sinirli_isaret**, ayrı inceleme mesajı **inceleme_gerekli**. 107 bulgunun 2'si inceleme (F01/F03), 105'i bağlam. Ek 40 paket yeni önemli risk alarmı üretmedi.
- Anlamlı yeni bağlam: **C-113**, 6 Ocak 2025 tarihli [KAP 1372848](https://www.kap.org.tr/tr/api/BildirimPdf/1372848) şirket açıklaması. Basında Özata Denizcilik'e atfedilen iş ortaklığının hâkim ortak Özata Tersanecilik'e ait olduğunu belirtiyor. Bu şirket beyanı, bağımsız doğrulama veya dolandırıcılık tespiti değildir. HTML'nin koşullu güncellenme gerekçesi bu kaynaklı ayrımdır; yalnız bulgu sayısının artması değildir.
- 94 belge, 148 finansal tutar, 29 gösterge, 59 iddia, 40 kurumsal gözlem, 25 kaynak beyanı, 2 nötr belge olgusu/fon pozisyonu, 6 geçmiş dönem ve 59 ret. Fon toplam değeri/iade koşulları gibi eksikler devam eder; belge karşılaştırması 0.
- Önceki 30 paketten ayrı kaynak/blok kimlikleriyle doğrulanan **40 yeni paket**: 12 iddia (11 operasyon, 1 karşı açıklama), 1 sahiplik gözlemi ve 3 gerçekleşme karşı açıklaması sağladı. Önceki paketlerin yeniden doğrulama farkları bunlara eklenmedi.
- Bu devam koşusunda finansal HTTP ve web kaynak keşfi kapalıydı. Önceki 30 paketlik koşuda keşif çalışmış, yeni uygun kaynak önerisi gelmemişti. Sonuç bütün web/fon kaynaklarının tarandığı anlamına gelmez.
- **30 önbellek kullanımı ve 61 yeni model çağrısı**; eski retli yanıtların güçlü tekrarları da bu sayıya dahil. Yeni başlatıcıdaki `--retry-cached` varsayılanı bu çalışma başladıktan sonra eklendi; bu koşuda uygulanmış gibi gösterilmez. Kaydedilmiş analiz süresi 809,4655 saniye (yaklaşık 13 dk 29 sn); yeni ayrıntılı aşama ölçümleri bu eski koşuda yok.
- HTML yalnız bu koşunun Analysis ve Assessment verilerini gömer. JSON indirmeleri, bütün bulgular/alıntılar, filtreler, kontrol izleri ve model denetimi korunur. Enron HTML'si değişmedi.
- Kontrol: iki JSON/hash/indirme eşliği, 1280/768/390 genişlikleri, yazdırma ve filtreler doğrulandı; dış HTTP isteği ve JavaScript hatası 0.

HTML SHA-256: `541aca72d85045bb8169d4ad640d3ddaa304046981734df74ed3ccfe88b95eb7`.
