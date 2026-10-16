# Gerekçeli inceleme öncelikleri

Güncelleme: 2026-10-16. Kural sürümü: `related-party-2`.

## Çalıştırma

```sh
uv run bilanco assess --run-id 88f8d197-9734-480e-9b46-3d374d963b1b
```

Kaynak çalışma bu PostgreSQL veritabanında kayıtlı olmalıdır. Komut veritabanındaki tamamlanmış `Analysis` kaydını okur; SEC iletişim adresi gerekmez ve veri indirilmez. Mevcut kişisel Codex CLI oturumuyla, web kapalı ek değerlendirme çağrıları yapılır.

Yeni `analyze` komutlarında aynı adım sayısal analizden sonra otomatik çalışır. Ek aşama en fazla sekiz çağrı ve ana analizin toplam çağrı bütçesinde kalan hakkı kullanır. Bütçe yetmezse işlenmeyen adaylar değerlendirilmedi olarak görünür. Modelin aynı anda çok sayıda bağımsız risk türünü değerlendirmesi istenmez.

Çıktılar `data/assessments/<yeni-kimlik>/assessment.json`, `assessment.md`, checkpoint ve AI çağrı kayıtlarıdır. Eski `Analysis` v1 JSON'u, raporu ve HTML demosu değiştirilmez. Veritabanında ek `bilanco.assessments` tablosu, kaynak çalışmaya yabancı anahtarla bağlanır. Şema sürümü 1'den 2'ye ek tablo/indeksle yükseltilir; önceki tablolar/kayıtlar silinmez.

## 2026-10-16 inceleme düzeltmeleri

Assessment şeması 1.1, kural related-party-2 ve AI görev assess_related_party_evidence_v3. Eski 1.0/related-party-1 JSON'ları okunabilir; eski kayıtlar yeni sonuç diye üzerine yazılmaz.

- Sıradan sözleşme koruması kişisel iş sözleşmesine daraltıldı. Yöneticinin yönettiği ayrı danışmanlık şirketine işlem sırf anlaşma adı yüzünden bağlam olmaz. kind ile açık bağlantı çelişirse belirsiz kalır.
- `transaction_scope` tek işlem (`single`), çoklu (`multiple`) veya belirsiz (`unknown`). Her model vakası tek bulgu kimliği taşır. Gerçekleşmiş işlem için tek minimal işlem alıntısı gerekir; çoklu/belirsiz kapsam veya birden fazla farklı işlem pasajı kabul edilmez, konu değerlendirilemeyen olarak korunur. Aynı bulgu birden fazla işlemi topluyorsa modele tek işlemmiş gibi cevap verdirmeyiz.
- Birleştirme aynı blokta olmaya değil aynı taraf ve tam işlem pasajına dayanır. Farklı işlemlerin unknown kontrolleri diğer işlemle doldurulmaz. Aynı işlemin yinelenen kanıtı tamamlanabilir.
- Açık olumsuz/önerilmiş işlem ve olumsuz bağımsız kontrol ifadeleri için çelişki koruması eklendi. Bu belirli karşı örnekleri engeller; genel anlam doğrulaması garantisi değildir.
- Açıkça grup içi/segment transferi için ayrı sınıf var; ayrıca desteklenmiş yönetici bağlantısı varsa bu sınıf önceliği bastırmaz. Kaynak sırası finansal önem sırası diye sunulmaz.
- Sürümü doğrulanmamış arşiv PDF'si yeni analiz veya değerlendirmeye alınmaz. SEC metadata tarihinin eski olması kopyanın sürümünü kanıtlamaz; özgün dosya yoksa başarısız/kısmi kapsam açık kalır.
- Ana analiz iptal edildiğinde kısmi dosyalar korunur, yeni assessment başlatılmaz, CLI 130 döner.
- Nakit used-in + pozitif basılı büyüklük işaret belirsizliğiyle reddedilir; zaten negatif tutar iki kez çevrilmez. Negatif özkaynak ayrı sayısal işarettir; mevcut sıfır/negatif payda veri yok diye sunulmaz.

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

Alıntı/konum/isim, bulgu kimlikleri, taraf adlarının kelime sınırları ve bazı açık hata durumları Python tarafından denetlenir. Doğrudan çalışanla yapılan sıradan iş sözleşmesi, ayrı karşı taraf yönetimiyle aynı sayılmaz. Sözcük eşleşmesi tek başına karşı taraf şirketine gerçek işlemi bastırmaz. Buna rağmen bu denetimler genel metin anlamını ispatlamaz; model değerlendirmesi otomatik öneri olarak kalır.

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

[48 yapay regresyon örneği ve değerlendirme komutları](../evaluation/README.md) geliştirme/regresyon-test olarak ayrılmıştır; önceki test görülmemiş holdout değildir. İnsan etiketleri tamamlanmamıştır; program bu alanları kendisi doldurmaz. Sayısal regresyon sonuçları finansal risk veya dolandırıcılık başarısı olarak yorumlanamaz.

Topluluk kontrolünde [Google AI'ın atomik rubrik ve kalibrasyon yazısı](https://dev.to/googleai/how-to-write-reliable-rubrics-for-llm-as-a-judge-evaluations-ndp) ve yorumlarındaki aynı hatayı birden çok sayma eleştirisi dikkate alındı. [Şema doğruluğu / kaynak doğruluğu ayrımı](https://dev.to/michael_maurice/schema-valid-correct-4-checks-before-you-trust-llm-extraction-4n6f) ve yorumlarındaki kaynak konumu uyarısı mevcut blok kimlikleriyle korundu. Bunlar bağımsız finansal başarı kanıtları değildir.

İşlem tekliği model beyanı ve bazı açık çoklu fiil kontrolleriyle sınırlandırılır; bu, her dilsel ifadede atomiklik ispatı değildir. Çoklu işlemi gizleyen veya anlamı yanlış etiketleyen model cevapları için insan değerlendirmesi ve farklı ifade karşı örnekleri hâlâ gereklidir.
