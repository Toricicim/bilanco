# Altı ajan incelemesinden sonraki düzeltmeler

2026-10-16. Önceki snapshot: 4953aeb / related-party-1. Yeni değerlendirme: related-party-2, Assessment 1.1, AI görevi assess_related_party_evidence_v3. Kaynak Analysis biçimi ve DB şeması değişmedi. Eski sonuçlar yeniden çalıştırılmış gibi etiketlenmedi.

| Konu | Yapılan değişiklik | Doğrulama |
|---|---|---|
| Yöneticiye bağlı danışmanlık şirketi | Kişisel çalışan sözleşmesi ile ayrı karşı taraf şirketine işlem ayrıldı; yanlış employment etiketi belirsiz kalır | Gerçek bağlı danışmanlık ödemesi first_review; kişisel olağan iş sözleşmesi context |
| Farklı işlemleri birleştirme | Model her bulguya ayrı vaka; tek minimal işlem pasajı ve açık scope zorunlu. Dedup tam işlem pasajına dayanır | Aynı bloktaki satış/kredi ve yes/unknown ayrı kalır; çoklu kapsam/finding/fiiller reddedilir |
| Nakit işareti | Used-in etiketiyle çelişen pozitif basılı büyüklük belirsiz sayılır | Olumlu nakit metni üretmez; zaten negatif tutar iki kez çevrilmez |
| Olumsuz/önerilmiş işlem | Açık olumsuzlama/öneri, yanlış yes ile kabul edilmez | No transaction / has never / did not sell reddi; not only ve kontrol yokluğu meşru işlemi bastırmaz |
| Bağımsız kontrol yokluğu | Açık olumsuz kontrol alıntısı reported_independent kabul edilmez | No independent valuation/audit committee review karşı örneği |
| Arşiv sürümü | Eski SEC metadata tarihiyle arşiv PDF kabulü kaldırıldı; eski archive_copy analiz yeniden değerlendirilemez | MockTransport ve saklı arşivden assessment testleri; modele ulaşmaz |
| Ctrl+C | İptal ayrı ai.cancelled alanında saklanır; ana CLI 130 ile durur | Kısmi Analysis kaydedilir, yeni assessment çağrılmaz |
| Negatif/sıfır payda | Mevcut tutar veri eksikliği sayılmaz; oran hesaplanmama nedeni açık; negatif özkaynak ayrı signal | Bilançosu denk, negatif özkaynaklı örnek ayrıca görünür |
| Grup içi aktarım ve üst liste | Açık intragroup_transfer sınıfı; ayrıca desteklenen yönetici bağı önceliği korur; kaynak sırası finansal önem değildir | Grup transferi context, gerçek yönetici bağında first_review |
| Ölçüm | Dört sınıf matrisi ve sınıf bazlı ölçümler, gereksiz uyarı/çekimserlik, ilk3 konu isabeti | Tüm negatifleri further_review veya unassessed yapma artık kapıdan geçmez |
| İlk aday kaçırmaları | End-to-end modu gerçek ilk extractor ile başlar; aday/hedef eşlemesi replay için saklanır | İlk extractor pozitif ilişkiyi atlayınca kaçırma görünür |
| Referans kapsamı | Hazır aday ile end-to-end beklentiler/insan etiketleri ayrı | Çok işlemli pasaj doğru ayrı çıkarılınca false positive sayılmaz; bir aşamanın insan etiketi diğerine taşınmaz |

## İki bağımsız doğrulayıcı

Birinci ajan veri/AI kurallarını, ikincisi ölçüm/CLI/edinim akışını inceledi. İlk turdaki dört dilsel/kapsam karşı örneği ve ölçümdeki aşama/insan etiketleme karışıklıkları düzeltildi; aynı ajanlar yeniden kontrol etti. Son kapsamlarında açık engelleyici bulgu bildirmediler. Bu, bütün olası model hatalarının ortadan kalktığı iddiası değildir.

Regresyon testleri `tests/test_review_fixes.py` içinde. Testler gerçek şirket edinimi/AI kullanmaz; PostgreSQL testleri yalnız bilanco_test_ isimli ayrı veritabanlarında çalışır.

## Tamamlanmış sayılmayan araştırma işleri

48 pasaj yapay regresyon setidir; 40 eski pasajın test bölümü artık görülmemiş holdout değildir. İnsan etiketleri boş bırakıldı. İki gerçek değerlendiriciyle alt sorular/kanıtlar, dört sınıf ve aşama bazlı beklentiler etiketlenmeli; yeni şirket/olay aileleriyle değerlendirme yapılmalı.

End-to-end deney ham metin bloklarından başlar; gerçek edinim/PDF ayrıştırma dahil tam finansal veri hattı performansı değildir. Ölçüm birimi pasajdır. Bir pasajdaki iki işlemin yalnız birini bulmak ile ikisini bulmak aynı en yüksek önceliği verebilir; bu yüzden sonuç işlem bazlı recall diye sunulmaz. Anahtar kelime/tek değerlendirme aşaması/tam iki aşama karşılaştırma yolları eklendi, ancak yeni canlı modellerle performans karşılaştırması bu düzeltme sırasında yapılmadı.

Alıntı/isim denetimi ve açık çelişki korumaları genel dilsel anlamın ispatı değildir. Transaction_scope model beyanıdır; tek pasaj/tek finding ve bazı çoklu eylem kontrolleri onu sınırlar, her dilsel ifade için atomik işlem kanıtı sağlamaz. Modelin Enron ön bilgisi silinmiş sayılmaz. İnsan doğrulaması ve genellenebilir risk başarısı hâlâ ölçülmelidir.

Mevcut Enron JSON/HTML related-party-1 koşusunun sabit kaydıdır. related-party-2 için yeni assess gerekir; bu düzeltme turunda canlı model veya yeni finansal veri çağrısı yapılmadı. Eski snapshot'ın gösterdiği bulgular bu değişikliklerle sessizce değiştirilmedi.

Son yerel doğrulama: izole PostgreSQL ile **148 test geçti**; Ruff lint/format ve git diff kontrolleri temiz. İki bağımsız ajan son değişiklikleri yeniden kontrol etti: veri/AI ajanında 106 hedef test ve eski/yeni karşı örnekler, ölçüm/akış ajanında 36 hedef test ve 5 bağımsız etiket/aşama kontrolü geçti. Ana finansal veritabanı kullanılmadı; geçici test DB kaldırıldı. Eski Assessment 1.0 kaydının okunabilirliği ve kaynak Analysis dosyasının değişmediği de kontrol edildi.
