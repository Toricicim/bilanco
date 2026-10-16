# Kayıtlı koşular — HTML gösterimleri

Güncelleme: 2026-10-16.

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

[ozatd-2025-03-31.html](ozatd-2025-03-31.html) tek dosyadır; indirip tarayıcıda açın. Sunucu/API/Codex/veritabanı gerektirmez. İnternet olmadan bulgular, kaynak alıntıları, hesaplar ve JSON indirmeleri çalışır.

- Kaynak koşu: `04d1cc5b-9fd5-42e1-b760-733b0ef574a1`; bilgi kesimi 2025-03-31 İstanbul gün sonu, finansal tablo dönemi 2024. Kural `tr-equity-review-1`.
- Sonuç: **sinirli_isaret**, durum **partial**. F01: 225.351.000 TL kâr karşısında −1.173.912.255 TL faaliyet nakdi. F03: nakit / kısa finansal borç yaklaşık %12,19. İki bulgu aynı finansal alanda; kapsamlı dikkat veya hile hükmü yok.
- 93 kabul edilmiş belge, 38 tutar, 18 gösterge, 128 bulgu (2 inceleme,126 bağlam) ve56 ret/çıkarım eksikliği gömülüdür. Belge kabulü bütün belgenin analiz edildiği anlamına gelmez. İlişkiler/denetim kapsamı yeterli sayılmadı; OCR/ek/sayı/AI bütçe sınırları gösterilir.
- Önceki gerçek koşuda32 yeni AI çağrısı yapıldı; düzeltme sonrası bu snapshot33 doğrulanan önbellek paketiyle,0 yeni çağrıyla hesaplandı. Tüm metinlerin tarandığı iddiası yok.
- Özet, kâr/nakit grafiği, düzey/alan/arama filtreleri, kaynak alıntıları ve konumları, bütün tutarlar/formüller, eksikler ve özgün iki JSON indirmesi bulunur. HTML üretirken ek analiz veya yeni risk puanı eklenmedi. Finansal yatırımlar nakit/borç oranına dahil değil; bilinmeyen likidite/blokaj açıklaması korunur.
- Ham JSON metinleri ve SHA-256 özetleri korunur. HTML SHA-256: `772b388ba8c5d6b8e76301e710c2e37f05c946eccfcc4dd44f45c6784d20c8c9`.
- Headless Chromium ile 1280/768/390 genişlikleri, taşma, bütün kayıtlar/alıntılar, filtreler, iki JSON'un tam eşliği/indirmesi, çevrimdışı çalışma ve yazdırma açılımı kontrol edildi. Dış HTTP isteği ve JS hatası0. Mobil/masaüstü/grafik ekran görüntüleri yerelde incelendi.
- Önceki Enron HTML/JSON ve eski kısmi OZATD tarama dosyaları değiştirilmedi. Bu, yeni program arayüzü değil; kullanıcının istediği ayrı kayıtlı sonuç gösterimidir.
