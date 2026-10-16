# Gerekçeli inceleme öncelikleri

Güncelleme: 2026-10-16. Kural sürümü: `related-party-1`.

## Çalıştırma

```sh
uv run bilanco assess --run-id 88f8d197-9734-480e-9b46-3d374d963b1b
```

Kaynak çalışma bu PostgreSQL veritabanında kayıtlı olmalıdır. Komut veritabanındaki tamamlanmış `Analysis` kaydını okur; SEC iletişim adresi gerekmez ve veri indirilmez. Mevcut kişisel Codex CLI oturumuyla, web kapalı ek değerlendirme çağrıları yapılır.

Yeni `analyze` komutlarında aynı adım sayısal analizden sonra otomatik çalışır. Ek aşama en fazla sekiz çağrı ve ana analizin toplam çağrı bütçesinde kalan hakkı kullanır. Bütçe yetmezse işlenmeyen adaylar değerlendirilmedi olarak görünür. Modelin aynı anda çok sayıda bağımsız risk türünü değerlendirmesi istenmez.

Çıktılar `data/assessments/<yeni-kimlik>/assessment.json`, `assessment.md`, checkpoint ve AI çağrı kayıtlarıdır. Eski `Analysis` v1 JSON'u, raporu ve HTML demosu değiştirilmez. Veritabanında ek `bilanco.assessments` tablosu, kaynak çalışmaya yabancı anahtarla bağlanır. Şema sürümü 1'den 2'ye ek tablo/indeksle yükseltilir; önceki tablolar/kayıtlar silinmez.

## Kaynak → değerlendirme → kural

Yalnız `related_party` ve `executive_conflict` adayları derinleştirilir. Tam aday bloğu ve aynı kaynaktaki komşu blokların en yakın 14'er satırı paketlenir. Gerekli blok aynı pakette ana kaynaksa tamamı korunur. Her alıntı asıl blok kimliğini taşır; kaynak tarihi ve kimliği korunur. Paket karakter sınırına bulgu/görev metni de dâhildir. Sığmayan, tarihi geçersiz veya alıntısı bulunamayan aday gizlenmez.

Model her konu için altı soruya `yes`, `no`, `unknown` veya `conflicting` cevabı ve alıntı verir:

1. Şirket yöneticisinin karşı tarafta yönetim/kontrol bağlantısı var mı?
2. Şirketle karşı taraf arasında gerçekleşmiş işlem var mı?
3. Bağlantı ve işlem aynı taraflara mı ait?
4. Finansal etki açıklanmış mı?
5. Bu işlemin ticari amacı açıklanmış mı?
6. Kontrol/onay/değerleme veya çıkar/oy sınırlamaları açıklanmış mı?

Sınıflandırmanın kendisi için de ayrı `classification_evidence` pasajı alınır; örneğin pasif sahiplikte altı sorunun tamamı belirsiz olsa bile bağlamın dayanağı kaybolmaz. Raporlayan şirketin tam adı veya kısa adı denetlenir; aynı kökü taşıyan farklı hukukî şirket biçimleri otomatik eşitlenmez.

İlk üç olumlu cevap birlikte varsa Python **öncelikli inceleme** önerir. İlişkili işlem var fakat koşullar tamamlanmıyorsa **ek inceleme**; sıradan sözleşme/sahiplik/tek başına ilişki varsa **bağlam**; temel ilişki çelişkili veya işlenmemişse **değerlendirilemedi** üretir. Öncelik risk şiddeti puanı değildir. Aynı öncelik içinde kaynak konumu ve sabit kimlik sırası kullanılır; AI'ın serbest sıralama tercihi kullanılmaz.

Kaynakta yalnız şirket yönetiminin beyanı bulunması bağımsız doğrulama sayılmaz. Bağımsız bir kontrolün raporda anlatılması da bu program tarafından bağımsız teyit yapıldığı anlamına gelmez. Açıklama bulunamaması `unknown` olur; `no` için açık olumsuz ifade gerekir. Bildirilen kontroller ayrı gösterilir ve sırf varlıkları bağlantıyı silmez. Tekrar eden alıntılar aynı ilişkiyi daha yüksek önceliğe taşımaz.

Alıntı/konum/isim, bulgu kimlikleri, taraf adlarının kelime sınırları ve bazı açık hata durumları Python tarafından denetlenir. Sıradan iş sözleşmesi üç model cevabı yanlışlıkla olumlu olsa bile tek başına öncelikli uyarıya dönüşmez. Buna rağmen bu denetimler genel metin anlamını ispatlamaz; model değerlendirmesi otomatik öneri olarak kalır.

## Rapor ve hata davranışı

- İlk üç öncelikli/ek inceleme konusu özetlenir; bütün konular ilgili bölümlerde tutulur.
- Destekleyen/dengeleyici pasajlar, eksik bilgiler, kaynak bulgu kimlikleri ve kural gerekçesi görünürdür.
- Mevcut sayısal göstergeler ve işaretler korunur. Önceki dönem cari oranı varsa son dönem değeriyle birlikte açıklanır; eski işaret güncel sorun gibi yeniden etiketlenmez.
- Diğer AI kategorileri kapsam dışında oldukları belirtilerek kaynak analizde korunur.
- Kaynak analizin `partial` durumu ile değerlendirme aşamasının tamamlanması ayrı kaydedilir. `complete`, tüm şirket risklerinin incelendiği anlamına gelmez.
- Model/çıkarım hatası kaynak sayıları silmez; eksik adaylar `unassessed` olur. Kısmi komut çıkışı 3; başarısız aşama 1; geçersiz girdi/bulunamayan çalışma 2'dir. Yeni analiz tamamlanmış olsa bile ek değerlendirme eksikse CLI çıkışı 3 olur; JSON'da iki aşamanın durumu ayrı görünür.
- Geçici bir model hatasında aynı paket tekrar denenmez; kalan bağımsız paketler mevcut bütçe içinde işlenir. Üst üste iki model hatasında veya araç/protokol ihlalinde kalan çağrılar durur. Başarısız paketler kapsam kaydında ayrıca sayılır.
- Her değerlendirme yeni kimlik ve kaynak analizinin kanonik JSON SHA-256 özetiyle kaydedilir. Önceki değerlendirme üzerine yazılmaz.

## Yöntem ve doğrulama sınırı

[PCAOB AS 2410](https://pcaobus.org/oversight/standards/auditing-standards/details/AS2410), ilişkilerin yanı sıra işlemin amacı/koşulları, onay ve yönetimin beyanını destekleyen/çürüten kanıtları incelemeyi ele alır. Burada yöntem geliştirme referansıdır; 2000 tarihli şirket kanıtlarına yeni standart veya sonraki olay bilgisi eklenmez. Program bir bağımsız denetim yürütmez.

[40 yapay örnek ve değerlendirme komutları](../evaluation/README.md) geliştirme/kilitli test olarak ayrılmıştır. İnsan etiketleri tamamlanmamıştır; program bu alanları kendisi doldurmaz. Sayısal regresyon sonuçları finansal risk veya dolandırıcılık başarısı olarak yorumlanamaz.

Topluluk kontrolünde [Google AI'ın atomik rubrik ve kalibrasyon yazısı](https://dev.to/googleai/how-to-write-reliable-rubrics-for-llm-as-a-judge-evaluations-ndp) ve yorumlarındaki aynı hatayı birden çok sayma eleştirisi dikkate alındı. [Şema doğruluğu / kaynak doğruluğu ayrımı](https://dev.to/michael_maurice/schema-valid-correct-4-checks-before-you-trust-llm-extraction-4n6f) ve yorumlarındaki kaynak konumu uyarısı mevcut blok kimlikleriyle korundu. Bunlar bağımsız finansal başarı kanıtları değildir.
