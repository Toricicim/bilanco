# İlişkili işlem değerlendirmesi için karşı örnekler

Güncelleme: 2026-10-15.

`related_party_cases.json`: tamamen yapay 40 pasaj; 20 geliştirme / 20 kilitli test örneği. Aynı olayın iki varyantı aynı ailede ve aynı bölümde tutulur. Kaynak metinler model paketine girer; beklenen etiketler ve insan değerlendirmeleri girmez. Açıklayıcı örnek adları da modele verilmez; `opaque-case-1` politikasında kaynak/bulgu kimlikleri SHA-256'dan türetilir. Eski açıklayıcı kimliklerle alınmış cevaplar yeni temiz değerlendirme yerine kullanılamaz.

**Beklenen etiketler önerilen kural cevaplarıdır. İki kişi tarafından etiketlenmiş bir altın standart değildir.** `reviewer_a` ve `reviewer_b` başlangıçta boştur. İki ekip üyesi önce aşağıdaki tanıma göre birbirinden bağımsız etiketlemeli; uyuşmazlıklar birlikte incelenmeli. Her alanın biçimi `{"reviewer_id": "gercek-kisi-kodu", "first_review": true}`. İki kişi aynı kimlik olamaz. Bu depodaki boş alanlar otomatik doldurulmaz.

Bir pasaj ancak raporlayan şirketin yöneticisinin karşı tarafta açık yönetim/kontrol bağlantısı **ve** aynı taraflar arasında gerçekleşmiş işlem birlikte destekleniyorsa `first_review=true` olur. İş sözleşmesi, pasif sahiplik, yalnız rol, başka karşı tarafla işlem, açık olumsuzlama ve gerçekleşmemiş teklif bu koşulu sağlamaz. Bildirilen kontroller mevcut bağlantıyı silmez; ayrıca gösterilir. Bu, suç/hile etiketi değildir.

```sh
uv run python evaluation/evaluate.py --split dev --run-model
uv run python evaluation/evaluate.py --split test --run-model
```

Bu açık komut gerçek Codex çağrıları yapar; gerçek şirket verisi indirmez, üretim veritabanına yazmaz. En fazla sekiz çağrı kullanır. Sonuç ve girdi/çıktı kayıtları `data/evaluations/<id>/` altında saklanır. Aynı cevapları yeni model çağrısı olmadan yeniden ölçmek için `--run-model` yerine `--predictions <assessment.json>` verilebilir.

Ölçümler: öncelikli inceleme için isabet/yakalama, yanlış pozitif/negatifler, kritik karşı örneklerde yanlış uyarı, insan görüş birliği ve eksik inceleme. İnsan etiketleri tamamlanmamışsa rapor bunu açıkça belirtir. `priority-abstention-1` ölçümünde `unassessed` başarılı negatif sayılmaz: ayrı `abstentions` listesine girer; beklenen pozitif kaçırıldıysa ayrıca FN sayılır. Düşük çağrı bütçesiyle kapsam tamamlanmadan kapı geçmez. Regresyon kapısı ayrıca beklenen pozitiflerin yakalanmasını ve yanlış öncelikli uyarı olmamasını ister; negatiflerdeki gerekçeli çekimserlik ayrıca görünür kalır.

Test bölümüne göre prompt/kurallar ayarlanırsa bu bölüm artık görülmemiş test olarak raporlanamaz; yeni bir test sürümü gerekir. Bu küçük yapay set genel şirket riski veya dolandırıcılık başarısını ölçmez.
