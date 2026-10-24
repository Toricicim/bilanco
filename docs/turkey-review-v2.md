# Türkiye incelemesi v2

Bu sayfa v2 değişikliklerinin tarihsel kaydıdır. Güncel sürüm ve KERVN desteği: [v3 yatırımcı gözlemleri](investor-checks.md).

Güncelleme: 2026-10-18. Kural `tr-equity-review-2`; yeni Analysis/Assessment şeması `1.1`, çıkarım istemi `tr-equity-extraction-3`. Eski dosyalar/snapshot'lar değiştirilmez. Enron akışı ayrı kalır.

## Ne düzeltildi?

- Türkçe kıvrık kesme işareti adın son ekini birleştirmez. Doğrulanmış ihraççının SAN./TİC. kısaltmaları kabul edilir. Karşı taraflar benzer adla otomatik eşitlenmez.
- `unknown` yönetici adı gerçek isim gibi aranmaz. Eksik isim, yönetici bağlantısı veya aynı taraf zincirini olumlu yapamaz. Reddedilen aday, kaynak kimliği ve kesin ret nedeni JSON'da korunur.
- Yönetici/tek işlem değerlendirmesinin yanında ayrı `observations` vardır: görev, sahiplik, ilişkili alış/satış, teminat, varlık işlemi, finansal yatırım. Dönem toplamı tekil yönetici işlemi kalıbına zorlanmaz.
- AI tutarı hesaplamaz; alıntıdan kopyalar. Kod alıntıyı/blok kimliğini, isimleri, tutar tokenını, tarihleri ve para birimini kontrol eder. Kontrol açıklaması bulunamaması `unknown`dur; `no` için açık yokluk beyanı gerekir. Yalanlanan iddia yokluk kanıtı kabul edilmez. Bunlar bütün anlam hatalarını eleyen bağımsız doğrulama değildir.
- Kısa/uzun finansal yatırımların `maturity` boyutu ayrıdır. Tek değeri olan iki sütunlu satırın sütunu tahmin edilmez. Aynı bildirimin doğrulanmış ekindeki açık satır kullanılabilir. Farklı kaynaklardaki tutarlar çelişirse otomatik tercih edilmez.
- Türkçe ay adları, Solo tablo kapsamı, DÖNEMİ bulunmayan başlık, dört sütunlu kümülatif/çeyreklik dönemler okunur. Genel konsolidasyon politikası şirket kapsamı yerine kullanılmaz. Başka ihraççıya ait ek finansal tablo, gövdede bu şirketin adı geçtiği için kullanılmaz.
- TMS29 dayanağı yalnız aynı bildirimde ve aynı kapsam/baz tarihinde bağlı ekten tamamlanır; kanıt konumları tutulur.
- Bir ekin hatası sonraki kardeş ekleri atlatmaz. Ret kaydı aşama/bildirim/objId/neden içerir. Kimlik araması yalnız ilk 10.000 karaktere bağlı değildir. Görüntü PDF'si okunmuş sayılmaz; OCR gereksinimi açık ret nedenidir. **OCR motoru eklenmedi.**
- Planlanan/işlenen/başarısız paketler ve kaynak bazlı ret/okuma eksikleri ayrı tutulur. Tek bir çıkarım reddi bütün denetim alanını 'hiç taranmadı'ya çevirmez. Yeni istem/şema eski AI önbelleğini kullanmaz.

## Normal şirketlere yanlış etiket koymama

`outcome` bir çöküş veya suç tahmini değildir. Eski F01–F05/O01–O02/M01 pilot eşikleri bu şirket uyarı versin diye gevşetilmedi. Eşiklerin gerçek şirketlerde kalibrasyonu tamamlanmış değildir.

1. Görev, sahiplik, ilişkili ticaret ve teminat tek başına alarm olmaz. Gerekli tarih/baz/para birimi eşleşirse açıklanmış maruziyet/özkaynak, ilişkili satış/hasılat veya yatırım/varlık oranı hesaplanır; bunlardan kayıp veya nakit çıkışı türetilmez. Alış toplamı gider ve varlık alışını karıştırabileceği için otomatik maliyet oranı hesaplanmaz.
2. Açık kontrol eksikliği/çelişkisi taşıyan yeni işlem adayı `R02/review` olarak ayrı kuyruğa alınabilir. **Kalibrasyona kadar `contributes_to_outcome=false`: genel şirket sonucuna oy vermez.** İnceleme adayı görünür kalır. Bu alan AI tarafından seçilemez; Python politikası belirler.
3. Onay/değerleme gibi karşı açıklamalar tutulur; bunlar tüm işlemlerin doğruluğunu garantilemez. Yoklukları da usulsüzlük kanıtı olmaz. Çelişkili adaylar tek kayda sessizce indirilmez.
4. F03 yalnız nakit/borç ölçer. Kısa vadeli finansal yatırımlar karşı kanıt olarak gösterilir. Nakit + yatırımlar duyarlılık oranı ayrıca hesaplanır; yatırım fonları otomatik likit/nakit kabul edilmez ve uyarı kendiliğinden silinmez.
5. F01/F03 aynı finansal alan içindedir; iki bağımsız oy sayılmaz. Yeni gözlem kayıtları eklenmesi şirket sonucunu kendiliğinden yükseltmez.
6. Olumsuz işaret yoksa fakat finansal/faaliyet/piyasa veya metin/kaynak kapsamı eksikse `yetersiz_veri` üretilir. `belirgin_isaret_yok` yalnız değerlendirilen kapsamda işaret olmadığını belirtir; şirketin güvenli olduğunu söylemez.

Ana çıktılar aynı konumdadır: `data/runs/<yeni-id>/analysis.json`, `assessment.json`, `report.md`. Assessment ayrıca `review_candidate_ids` ve `calibration_status=not_calibrated` içerir. Kaynak/tarih kontrolleri ve sayısal kurallar Python'da, kaynak pasajı adayları AI'dadır. Program HTML üretmez.

## İddia ile testin hedefini ayır

Finansal sıkıntı, ilişkili işlem yönetişimi, muhasebe hilesi ve işlem bazlı piyasa manipülasyonu aynı sonuç değişkeni değildir. Kamuya açık rapor incelemesinin gizli emir/hesap koordinasyonunu kanıtladığı iddia edilemez. SPK'nın bir hisse piyasası tedbiri, ihraççının muhasebe hilesi etiketi değildir.

Resmî dayanaklar (2026-10-18 kontrolü): [KGK TMS24](https://kgk.gov.tr/Portalv2Uploads/files/Duyurular/v2/TMS/TMS_2020/TMS%2024.pdf) ilişkili ilişkilerin ticaretin normal bir parçası olabildiğini ve işlem/taahhütlerin açıklanmasını ele alır; [SPK işlem bazlı piyasa dolandırıcılığı](https://spk.gov.tr/yatirimcilar/sermaye-piyasasinda-piyasa-dolandiriciligi-manipulasyon/islem-bazli-piyasa-dolandiriciligi) emir/işlem/hesap hareketi mekanizmasını açıklar. Mevzuat otomatik suç sınıflandırıcısına çevrilmedi.

## Gerçek başarıyı nasıl ölçeceğiz?

Henüz yapılmamış deney protokolü:

- Birincil hedefi önceden yaz: örneğin belgeye dayalı maddi finansal/yönetişim inceleme işareti. Sonraki fiyat düşüşünü otomatik hile etiketi yapma. Şirketin hile olayı ve piyasadaki yatırımcının fiili ayrı etiketlerdir.
- Olay şirketleri yanında sektör, büyüklük ve halka arz yaşı benzer, izlem döneminde hedef olay kaydı bulunmayan karşılaştırmalar seç. Bunlara 'kesin temiz' etiketi verme. Kuralları Özata'ya göre ayarladıktan sonra Özata'yı bağımsız test diye kullanma.
- Her kesimde yalnız o tarihte yayımlanmış belge/versiyon olsun; olay sonrası kaynaklar yalnız değerlendirme etiketinde dursun. Eğitim bilgisi taşıyan model yüzünden tam körlük garantisi verme; gerekirse kimlik maskeleme duyarlılık deneyi yap.
- İki değerlendirici kaynak pasajlarını bağımsız etiketlesin; uyuşmazlığı kayıtla çöz. Rol/işlem yakalama doğruluğu ile şirket uyarısı başarısını ayrı ölç.
- Şirketleri ayırarak geliştirme ve saklı test grubu oluştur. Eşik/istem/eksik veri politikasını testten önce dondur; değişirse yeni sürüm ve yeni test gerekir.
- Yanlış alarm oranı, uyarıların doğruluğu, yakalama oranı, ilk uyarı süresi, veri kapsamı ve karar verilemeyen oranı birlikte raporla; küçük örneklem için belirsizlik aralıkları ver. Eksikleri negatif örnek gibi sayma. Tek şirket öncesi/sonrası ve yapay testler genellenebilir başarı kanıtı değildir.

## Mühendislik kaynakları

İki DEV yazısı ve yorumları incelendi; topluluk uzlaşısı veya finansal doğrulama sayılmadı. [Hitarth Desai — Dead-Letter Queues for LLM Extraction Failures](https://dev.to/hitarthbuilds/dead-letter-queues-for-llm-extraction-failures-capture-triage-and-replay-without-losing-trust-4598), reddedilen kaydın nedeni/kanıtı/sürümüyle saklanmasını tartışıyor. [Michael Maurice — Schema-Valid Isn't Correct](https://dev.to/michael_maurice/schema-valid-correct-4-checks-before-you-trust-llm-extraction-4n6f) ve altındaki yorum, şema ve alıntı eşleşmesinin doğru bağlamı garanti etmediğini vurguluyor. Burada blok konumu ve ret kaydı korundu; önerilen ürünler kurulmadı.
