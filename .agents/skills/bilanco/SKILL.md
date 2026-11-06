---
name: bilanco
description: Türk borsa hisseleri için Bilanco programıyla kaynaklı inceleme yap, şirket kimliğini doğrula ve kayıtlı bulgular üzerinden inceleme önceliklerini açıkla. Kullanıcı Bilanco modunu istediğinde veya bu programla bir hisseyi araştırmak istediğinde kullan.
---

# Bilanco inceleme modu

Kullanıcıyla Türkçe ve kısa konuş. Bu skill etkinleştiğinde, konuşma başka bir işe geçene veya kullanıcı moddan çıkana kadar hisse incelemesi takip sorularında aynı kayıtlı çalışmayı kullan. Mod açılması tek başına veri indirme veya model analizi talebi değildir. Yalnız mod istenmişse “Bilanco hazır. Hangi hisseyi inceleyelim? Eski bir tarih seçebilirsin; hisse belli olunca10/20/40 paketlik okuma seçeneklerini ve önerimi göstereceğim.” diye sor.

Codex CLI'da desteklenen çağrı `$bilanco` veya `/skills` içinden Bilanco seçimidir. `/bilanco` metni sana iletilirse aynı niyet olarak ele al; CLI'ın tanımadığı slash komutunu kaydedebildiğini iddia etme.

## Program bağlantısı

Bu skill dizinindeki `scripts/bilanco.py` yardımcı programını Python ile çalıştır. Yardımcı program bağlı repo kökünü bulur ve orada `uv run bilanco` çağırır; komut argümanlarını shell metnine birleştirme. Skill klasörü başka yere kopyalanmış ve repo bulunamıyorsa kullanıcıdan repo konumunu iste; tahmin edilen bir projede çalıştırma.

- `python <skill-dir>/scripts/bilanco.py company list`: yerleşik ve doğrulanmış yerel şirketler; ağ/model çağrısı yok.
- `python <skill-dir>/scripts/bilanco.py company show --ticker KOD`: yerel şirket kimliğini kontrol et.
- `python <skill-dir>/scripts/bilanco.py company add --ticker KOD --kap-url https://www.kap.org.tr/tr/Bildirim/ID`: yeni şirketi resmî metadata ve kendi PDF'sinden doğrula/kaydet. Finansal inceleme veya AI çağrısı yapmaz; iki resmî belgeyi edinir.
- `python <skill-dir>/scripts/bilanco.py prepare --company KOD --as-of YYYY-MM-DD`: kayıtlı kapsamı ve10/20/40 paket seçeneklerini JSON olarak getirir; yeni belge/model analizi başlatmaz.
- `python <skill-dir>/scripts/bilanco.py analyze --company KOD --as-of YYYY-MM-DD --max-packets 10 --max-ai-calls 22`: gerçek veri/model analizi. Çıktı JSON, ilerleme stderr. Çıkış3 kısmi rapor oluşabildiğini,130 iptali gösterir; sırf3geldi diye yeniden başlatma.

## Şirketi ve tarihi belirle

Kullanıcının verdiği hisse kodunu kullan. Yalnız isim verdiyse önce yerel listede tam şirketi belirle; birden fazla olası şirket varsa seçim iste. Kayıt yoksa web araması mevcutsa şirketin resmî KAP bildirim URL'sini bul. Aramada kod–tam unvan eşleşmesini kontrol et. KAP üye kimliği, ilk işlem tarihi veya risk hükmü uydurma. Web yoksa ya da özgün bağlantı bulunamıyorsa kullanıcıdan KAP bildirim bağlantısını iste. Sonsuz arama/tekrar yapma; iki başarısız adaydan sonra eksikliği bildir.

Bulduğun URL yalnız adaydır. `company add` başarılı olmadan şirketi doğrulanmış sayma. Python kaynaktan kod/unvan/kimliği çıkarır; ham AI JSON'u şirket kaydı olarak yazma. Kimlik belgesi kesimden sonra yayımlanmış olabilir; yalnız yönlendirme içindir, geçmiş finansal kanıt olarak sunma. İlk işlem tarihi ve eski unvan/kod bağlantıları doğrulanmamış olabilir. Banka/sigorta gibi farklı rapor yapılarında mevcut kontrollerin destek kapsamını açıkla; genel kod desteğini sektör başarısı diye sunma.

Tarih verilmişse onu koru. Tarih belirtilmemiş güncel incelemede bugünün İstanbul tarihini açıkça belirtip kullan; olay öncesi testte kesim belirsizse önce sor. Sonraki olayın sonucunu geçmiş veri paketine ekleme.

## İncelemeyi çalıştır ve sonucu açıkla

Kullanıcı “araştır/incele” diyorsa analiz talebidir; yalnız mod açmak veya nasıl çalıştığını sormak değildir. Şirket/tarih belli olunca önce `prepare` çalıştır. `mode=finished` ise kayıtlı sonucu sun, otomatik yeni edinim yapma. Diğer durumlarda `options` içindeki10/20/40 paket seçeneklerini, varsa mevcut işlenen/toplam kapsamı, ek miktarı ve çağrı tavanını açıkla. `recommendation` gerekçesini sadeleştirerek “İlk turda10 paket öneririm; kapsamı ve eksikleri gördükten sonra artırabiliriz” veya devam karşılığını söyle. Paketlerin belge parçaları olduğunu;10 paketin10dosya demek olmadığını belirt. Kalan paket10dan azsa öneriyi gerçek kalan miktara göre söyle. Kullanıcıya hangisini istediğini sor ve cevabını bekle. Salt “incele” talebi bu seçimi cevaplamaz. Kullanıcı isteğinde açıkça paket bütçesi verdiyse tekrar sorma; toplam/ek ayrımını koru. Bütçe tercih edilmeden analiz başlatma. Hazırlık kaydı yapay bir risk sonucu veya süre tahmini değildir. Başlamadan şirketi, kesimi ve seçilen bütçeyi kısa bildir. Şirket kimliği araması için Python içinden ikinci Codex araması açma. İç motorun belge çıkarım çağrıları devam eder; üst sohbet/web tüketimi `analysis.ai.calls` sayacına dahil değildir.

`prepare` bir `resume_run` verdiyse bu tarihli kayıttan devam seçeneğini kullan; ilk tur gibi sıfırdan başlatma. Devam istenmişse önce kaydın `run_id`, şirket/tarih ve `packets_processed`/`packets_planned` alanlarını kontrol et. İstenen ek miktarı toplam hedefe ekleyerek `--resume-run UUID --offline --no-discover` kullan. Örneğin30+20için `--max-packets 50 --max-ai-calls 40`. Kalan kapsam daha azsa sınırla. Önceki UUID bu bilgisayarda yoksa mevcutmuş gibi davranma. Retli önbellek için `--retry-cached` kendiliğinden ekleme.

Komutun verdiği `analysis.json`, `assessment.json`, `report.md` yollarını oku. Görüşünü şirket hakkında hafızadan bildiklerinle doldurma. Önce mevcut `review/critical` bulguları, gerekçeleri, kaynakları ve karşı açıklamalarını göster; sonra eksik kapsamı ve kalan paketleri belirt. Mevcut kuyruk kalibre edilmiş bir önem sıralaması değildir; daha güçlü sıralama/çöküş olasılığı uydurma. AI önerisi eklemek gerekiyorsa program çıktısından ayrı ve açıkça öneri olarak göster.

Takip sorularında aynı kayıt ve kaynak alıntılarını kullan. Yeni tarama yalnız kullanıcı isterse. HTML yalnız ayrıca istenirse kayıtlı veriden hazırlanır. Sırları, `.env` içeriğini ve Codex kimlik bilgilerini okuma/yazdırma. TLS/erişim engelini aşma. Kullanıcı “moddan çık” dediğinde normal konuşmaya dön.
