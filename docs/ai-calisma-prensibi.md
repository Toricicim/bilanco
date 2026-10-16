# AI şu an nasıl çalışıyor?

Güncelleme: 2026-10-16. Bu metin mevcut kodu anlatır; gelecek özellik planı değildir.

```text
Analiz komutu
  → Python: belgeyi al, şirketi ve yayın tarihini kontrol et
  → AI: eksik bilgi için ek kaynak adresleri öner
  → Python: adresleri, belgeleri ve tarihlerini tekrar kontrol et
  → Python: tablolardan sayıları çıkar, oranları ve kural bulgularını hesapla
  → AI: belge parçalarında alıntılı ilişki/koşul adayları bul
  → Python: alıntı, belge konumu ve isim eşleşmesini kontrol et
  → AI: mevcut bulguların okuma sırasını öner
  → Python: JSON + Markdown dosyalarını ve veritabanı kayıtlarını oluştur
  → AI: yönetici/ilişkili işlem adaylarını alıntılı alt sorularla değerlendir
  → Python: sabit öncelik kurallarını uygula, ayrı Assessment JSON + Markdown kaydet
```

## AI ne zaman çağrılıyor?

- **Kaynak keşfi:** Her analizde bir kez. Program eksik kavram/dönem listesini ve ek resmî açıklama ihtiyacını gönderir. AI en fazla beş URL döndürür. Arama özeti finansal veri olarak kabul edilmez. Kabul edilmiş yıllık rapor varsa aynı raporun PDF kopyası tekrar işlenmez.
- **Belge okuma:** Kabul edilen bütün metin blokları, boyut sınırına göre paketlenerek gönderilir. Önce bir risk kuralının tetiklenmesi gerekmez. Bu çağrıda web araması kapalıdır; yalnız verilen metin kanıttır. Hata veya çağrı bütçesi nedeniyle okunamayan paket varsa kayda geçer.
- **Sıralama:** En az bir bulgu varsa bir kez. AI yalnız mevcut bulgu kimliklerinin sırasını ve kısa/ayrıntılı gösterim tercihini döndürür. Mevcut Markdown üreticisi bu tercihten sırayı uygular; serbest AI raporu yazmaz.
- **İnceleme önceliği:** Yeni `analyze` çalışmalarının sonunda veya `assess --run-id` komutuyla ayrıca çalışır. AI yönetici bağlantısı, işlem, aynı taraflar, finansal etki, amaç ve kontroller için alıntılı cevap verir. Python kaynak kontrollerinden sonra öncelik kuralını uygular. Bu yeni raporun sırası AI'ın serbest sunum tercihi değildir. [Ayrıntılar](assessment.md).

Program bug'ı, HTTP hatası veya eksik rakam “şirkette sorun var” diye AI'a yorumlatılmaz. Kod hatalarını geliştirici çözer. Modelin çıktısının geçersiz olması da şirket riski değildir.

## Enron üzerinden doğal örnek

Kullanıcı `enron / 2000-03-31` analizi başlatır. Program, o tarihe kadar yayımlanmış özgün raporu kabul eder.

**Sayı tarafı:** Python net kâr ve faaliyet nakdi satırlarını, dönemlerini ve birimlerini okur. Kâr artarken faaliyet nakdi düşüyorsa kodda yazılı kural bir inceleme işareti üretir. Bu hesap için AI'a soru sorulmaz. Faaliyet nakdinin pozitif olması gibi dengeleyici bilgi de korunur.

**Metin tarafı:** Program bir dipnot paketini AI'a şu görevle yollar: “Bu metinde yönetici–karşı taraf ilişkisi, ilişkili işlem, garanti, kredi koşulu, denetçi görüşü veya yönetimin dengeleyici açıklaması var mı? Varsa kaynak cümlesini aynen al.”

AI'ın cevap biçimi bir sohbet paragrafı değil, şu alanları içeren JSON'dur:

- `kind`: örneğin `executive_conflict` — yönetici–karşı taraf ilişkisi adayı.
- `block_id`: kendisine verilen belge bloğunun kimliği.
- `quote`: o bloktan aynen alınmış pasaj.
- `actor`, `counterparty`: alıntıda aynen geçen taraflar; yoksa boş.

Bu, **cevabın yapısını anlatan örnektir**; belirli bir canlı model cevabı gibi sunulmaz. Gerçek çağrılar ilgili çalışmanın `ai/*-input.json`, `*-output.json`, `*-receipt.json` dosyalarındadır.

Python alıntının o blokta bulunduğunu ve isimlerin alıntıda geçtiğini denetler. Eşleşmezse adayı reddeder. Eşleşirse **“anlam doğrulaması gerekli”** olarak kaydeder. Kontrol, alıntının varlığını doğrular; ilişkinin gerçekten çıkar çatışması olduğunu otomatik ispatlamaz.

İlk analizdeki sıralama çağrısı bu adayla hesaplanmış bulguların okuma sırasını seçer. Python kaynaklı analiz raporunu oluşturur. Ardından ek değerlendirme aynı yönetici bağlantısını gerçekleşmiş işlemle birleştirebilirse “öncelikli inceleme” önerir; dengeleyici açıklamalar ve eksik bilgiler yanında kalır. Sonuç “Enron dolandırıcıdır” veya “şu tarihte çökecek” değildir.

## Bağlantı ve kayıt

- Program her görev için yeni bir `codex exec` süreci açar; bu sohbetin devamını çağırmaz. Mevcut kişisel CLI oturumu kullanılır. Bu sürüm kendi modelimizi eğitmez.
- Ana işleyiş `src/bilanco/pipeline.py`, görevler ve kontroller `src/bilanco/ai.py`, sayısal kurallar `src/bilanco/calculations.py` içindedir.
- Sonuçlar `data/runs/<run_id>/analysis.json` ve `report.md` dosyalarında, ayrıca PostgreSQL'de tutulur. Bu sürümde arayüz ve otomatik insan onay ekranı yoktur.
- Ek değerlendirme `data/assessments/<id>/assessment.json` ve `assessment.md` dosyalarına, ayrıca `assessments` tablosuna yazılır. Kaynak analiz değiştirilmez; insan kalibrasyonu tamamlanmış gibi gösterilmez.
- Eğitimden gelen Enron bilgisi modelden silinemez. Tarih filtresi ve kaynak zorunluluğu bunu bütünüyle kör tahmin deneyi hâline getirmez.
