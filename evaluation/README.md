# İlişkili işlem değerlendirme deneyleri

Güncelleme: 2026-10-16. Kural `related-party-2`, ölçüm `priority-four-class-2`.

`related_party_cases.json`: **48 yapay pasaj**, 24 geliştirme / 24 regresyon-test. Eski 40 pasaj geliştirmede incelendiği için test bölümü artık görülmemiş holdout diye sunulmaz. Aynı olayın varyantları aynı aile/bölümde kalır. Yeni aileler: yöneticiye ait danışmanlık şirketine işlem, grup içi gerçek transfer, birden fazla işlem ve açıkça reddedilmiş bağımsız kontrol.

**Etiketler önerilen kural beklentileridir; insan altın standardı değildir.** `reviewer_a` / `reviewer_b` boş bırakılmıştır. İki gerçek kişi, model çıktısını görmeden bağımsız etiketlemeli. Örnek alan:

```json
{"reviewer_id":"gercek-kisi-kodu","first_review":false,"priority":"context"}
```

İki kişinin kimliği farklı, iki cevabı tutarlı olmalıdır. `priority`: `first_review`, `further_review`, `context`, `unassessed`. Öncelik sınıfı etiketi olmayan eski boolean insan etiketi dört sınıfı doğrulanmış yapmaz. Rol/işlem/aynı taraf alt cevapları ve kanıt konumları da insan incelemesinde ayrıca kaydedilmelidir; bu dosyalar otomatik doldurulmaz.

## Üç karşılaştırma

```sh
# Basit, dondurulmuş anahtar kelime karşılaştırıcısı; AI çağrısı yok
uv run python evaluation/evaluate.py --split dev --baseline

# Tek model aşaması: adaylar önceden verilir, yalnız değerlendirme ölçülür
uv run python evaluation/evaluate.py --split dev --stage assessment --run-model

# Ham metin bloklarından: gerçek ilk AI çıkarımı + değerlendirme
uv run python evaluation/evaluate.py --split dev --stage end-to-end --run-model
```

`--run-model` açıkça gerçek Codex çağırır; diğer komutlar çağırmaz. Finansal veri indirilmez; üretim DB kullanılmaz. Metinler halen kısa yapay bloklardır: gerçek uzun çok belgeli raporlar için görülmemiş şirket/olay ailelerinden ayrı veri gerekir. Anahtar kelime tabanı bilerek basit, doğrulanmamış bir karşılaştırıcıdır. Model veya yeni yöntemin daha başarılı olduğu bu komutları eklemekle kanıtlanmış sayılmaz.

Uçtan uca deneyde adaylar önceden üretilmez. `extract_from_blocks` gerçek `Codex.extract` ve kaynak doğrulamasını çalıştırır. Sonra ilişkili işlem adayları değerlendirilir; iki aşama aynı toplam çağrı bütçesini paylaşır. İlk aşamada atlanan/yanlış kapsamda sınıflandırılan pozitif hedefler kaçırma olarak görünür. Hiç aday çıkmaması “uyarı üretilmedi” olarak değerlendirilir; incelenmiş ilişki sayılmaz. `candidate_coverage` son değerlendirmede temsil edilen ilgili hedef oranıdır; ilk aşama aday sayısı `extraction.candidate_count` içinde ayrı tutulur. Bu ayrım bütün metnin anlaşıldığı iddiasını engeller.

## Ölçüm ve tekrar oynatma

Çıktılar `data/evaluations/<id>/` altındadır. Dört sınıf karışıklık tablosu, sınıf bazında precision/recall, gereksiz uyarı, kaçırılan pozitif, kaçınılabilir çekimserlik ve ilk üç önerinin konu isabeti raporlanır. İlk üç ölçümü finansal tehlike sıralamasının doğruluğu değildir. Eski `first_review` TP/FP/FN/TN de karşılaştırma için korunur; `unassessed` TN sayılmaz.

Yeni regresyon kapısı yalnız ikili başarıyla geçmez: dört sınıf etiketlerinin tamamlanması, bütün sınıfların geçici beklentileri karşılaması ve aşamanın complete olması gerekir. İnsan değerlendirmesi ayrı gösterilir; bu katı mühendislik kapısı yatırım/hile doğrulaması değildir. Bilerek belirsiz örnek için unassessed doğru beklenti olabilir; bütün çekimserlikler zorla hataya çevrilmez.

```sh
# Kayıtlı assessment-only çıktısını yeni çağrı olmadan ölç
uv run python evaluation/evaluate.py --split dev --predictions path/to/assessment.json

# End-to-end replay için ilk çıkarımın gerçek eşlemesi gerekir
uv run python evaluation/evaluate.py --split dev --stage end-to-end \
  --predictions path/to/assessment.json --candidate-map path/to/candidate-map.json
```

Beklenen etiketler/aile adları/insan değerlendirmeleri modele gönderilmez; kimlikler hash tabanlıdır. Eski 40 pasajlık dosyalar yeni 48 pasajlık seti kapsamaz; sessizce tam ölçüm gibi yeniden etiketlenmez. Eski ölçümler kendi sürümlerinde tarihsel kayıt olarak kalır.

Ölçüm birimi pasaj/hedef ailesidir; çok işlemli pasajda en yüksek görünen öncelik alınır. İki ayrı işlemin ikisini de bulma oranı bu metrikten çıkarılamaz. `multiple_transactions` örneği hazır tek aday olarak sunulunca `unassessed`, ilk çıkarım iki işlemi ayırabildiğinde uçtan uca `first_review` bekler; `expected_end_to_end_priority_provisional` ayrı beklentiyi taşır. İnsanlar bu aşama için ayrıca `end_to_end_priority` etiketlemeli; hazır aday etiketi uçtan uca altın standart yerine geçmez.
