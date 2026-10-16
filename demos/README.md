# Kayıtlı Enron koşusu — HTML gösterimi

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
