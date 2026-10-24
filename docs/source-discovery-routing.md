# Tarihli kaynak keşfi ve sınırlı model yükseltme

Güncelleme: 2026-10-24. Türkiye `analyze` akışı; Enron yolu korunur. Yeni risk eşiği/başarı oranı eklenmedi.

## Çalıştırma

En kısa yol `./baslat`: şirket/tarih ve 10/20/40 yeni paket seçilir. Aynı tarihli en kapsamlı uyumlu yerel kayıttan devam edilir; devam menüsü web keşfini ve finansal HTTP'yi kapatır. [Başlatma, bütçe ve bitiş özeti](../README.md#hızlı-başlatma).

```sh
uv run bilanco analyze --company ozatd --as-of 2025-03-31 --max-packets 30 --max-ai-calls 64
# Veritabanınızda önceki koşu varsa; eski dosyaları değiştirmeden yeni koşu:
uv run bilanco analyze --company ozatd --as-of 2025-03-31 --resume-run ONCEKI_UUID --max-packets 30 --max-ai-calls 64
```

- `--max-packets` varsayılan **30 toplam işlenmiş paket**; önbellek kullanımları dahildir. 30 yeni çağrı anlamına gelmez. Okunmayanlar `skipped_packet_limit`, gerçek model hatası `failed` olur.
- `--max-ai-calls` fiziksel çağrılar için ortak sınırdır: ilk çıkarım + güçlü tekrar + web keşfi. Verilmezse `.env` bütçesi (varsayılan32) geçer; 64 yalnız yukarıdaki açık komutun sınırıdır. Başarılı pakette reddedilen adaylar kalabilir; bu tam doğrulama anlamına gelmez.
- `--model` veya `BILANCO_CODEX_MODEL` ilk modeli seçer; ikisi de boşsa Türkiye komutunda `gpt-6-luna`. `--fallback-model` varsayılan `gpt-6.1-sol`. Enron'un mevcut model seçimi korunur. Farklı hesaplarda model erişimi ayrıca sınanmalıdır.
- `--no-discover` web keşfini kapatır. `--offline` finansal HTTP'yi ve web keşfini kapatır; çıkarım için Codex bağlantısı ve yerel belge paketi veya `--resume-run` gerekir.
- `--resume-run` aynı şirket/kesim tarihi, önceki Analysis/Assessment özeti ve ham dosya hash'lerini doğrular. Kaynakları/fiyatları yeniden kullanır; eski risk sonucunu girdiye taşımaz. Kaynak/DB dosyaları Git'te olmadığından başka bilgisayar o UUID ile başlayamaz; normal analyze veya kendi yerel koşusu gerekir.

## Sıra

1. Normal KAP/Yahoo edinimi veya doğrulanan önceki kaynaklar.
2. Önce en fazla9 ilk rapor paketi; kabul edilen nötr fon pozisyonlarından kodlar elde edilir. Finansal hesaplar Python'da.
3. Ayrı Codex çağrısında web araması açılır. Hedef şirket ve yalnız tarihli kanıtta bulunan en fazla4 fon kodudur. Nötr belge sorguları kullanılır; skandal/sonraki olay anlatısı istenmez.
4. Model en fazla5 kaynak adresi/hedef/tüzel ad önerir. Arama özetinden tutar, tarih veya risk sonucu alınmaz. İlk arama boşsa güçlü modelle en fazla bir **kapsam denemesi** yapılır; boşluk doğrulama hatası sayılmaz.
5. Python yalnız izinli HTTPS KAP Bildirim/ID veya BildirimPdf/ID adresini indirir. PDF'de kendi kalıcı kimliği, yayın saati ve tüzel kişi doğrulanır. Fon için kodun kendi kapağında bulunması gerekir; portföy tablosunda bir kod görmek fon kimliği değildir. Kesim sonrası belge, belirsiz kimlik, dış alan adı ve tekrar reddedilir.
6. Kabul edilen belgenin KAP ek metadata kaydı aynı bildirim/tarihe bağlanır; en fazla10 PDF eki kendi kimliğiyle doğrulanır. Ek veya metadata hatası kapsam eksikliği olarak korunur. Fon kaynağı issuer tablosuna/ilişki adayına dönüşmez.
7. Yeni kaynakların paketleri önce işlenir, sonra ilk havuzun kalanları; toplam işlenen sınırına kadar. Keşif önerisi bulunamazsa kaynak havuzu büyümez; eski havuzda30'a kadar devam edilir.
8. Çıkarımda web kapalıdır. Şema/protokol hatasında tek güçlü deneme; alıntı/tarih/tutar/kimlik doğrulamasının reddettiği aday varsa aynı kapalı paketle tek güçlü yeniden çıkarım yapılır. İki yanıt da kaydedilir; daha az mekanik retli yanıt seçilir ve geçmeyen adaylar yine reddedilir. Hata sonrası doğrudan güçlü yanıt alınmışsa aynı paket ikinci kez yükseltilmez.
9. Kurallar, hesaplar, karşı açıklamalar ve veri eksikleriyle yeni Analysis/Assessment/Markdown yazılır. HTML bu programın adımı değildir.

## Önbellek ve denetim

Çıkarım istemi5 korunur. Anahtar belge paketi, şema/istem ve istenen ilk modele bağlıdır. Seçilen güçlü yanıtın gerçek model adı zarf içinde saklanır. Açık bir devam koşusunda, önceki işlenmiş aynı kaynak/blok paketleri için eski boş model ayarının önbelleği de denenebilir; hash ve tüm kanıt kontrolleri yeniden uygulanır. Eski9 yanıt silinmez. Önbellekteki geçmeyen adaylar yeniden doğrulanıp reddedilir; varsayılan olarak tekrar güçlü model çağrısı yapılmaz. `--retry-cached` verilirse önbellek doğrulama retleri için de tek güçlü tekrar denenir. Yeni paketlerdeki tek güçlü tekrar politikası değişmez. Böylece paket ekleme bütçesi önceki retleri tekrar tekrar denemeye harcanmaz; önceki hatalar kabul edilmiş sayılmaz.

`analysis.ai`: `discovery` (öneri/kabul/ret/ekler), `source_origins`, `model_routes`, `packet_manifest`, `packet_limit`, `cache_hits`, `calls`, `receipts`, `resumed_from`. `ai/primary/` ve `ai/fallback/` tam giriş/şemalı çıkış/makbuzları saklar; kullanım/süre ve model seçimi görünür. Bunlar yerel ve gitignored'dır.

## Gerçek sınırlar

- Şema ve alıntı denetimi, anlamın tam doğruluğunu/eksiksizliğini kanıtlamaz. Boş yanıt veya güzel görünen yanlış çıkarım otomatik yakalanamayabilir. Güçlü model de hatalı olabilir. Ret sayısındaki düşüş araştırma başarısı ölçüsü değildir.
- Web araması günümüzde yapılır; modelin sonraki bilgisini silmez. Belge kabulü tarih kontrollüdür, kaynak seçimi tam kör değildir. Hakemli geçmiş başarı deneyi için önceden sabit kaynak evreni/olay protokolü gerekir.
- KAP dışındaki siteler bu ilk Türkiye keşif adaptöründe otomatik kanıt alınmaz. Fon kataloğu/TEFAS sürekli tarihsel arşivi, sınırsız ağ taraması, OCR ve emir/saklama yoktur. Boş keşif veya okunmayan paket, güvenlik göstergesi değildir.
- İncelenmiş paket sayısı, tüm şirketin ekonomik ilişkilerinin veya30 bağımsız belgenin incelendiği anlamına gelmez. Aynı uzun rapor birden çok paket oluşturur.

Model seçimi resmî belgeleri (23 Ekim2026 kontrolü): [model kataloğu](https://developers.openai.com/api/docs/models), [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna). İki model de bu ortamda yalnız yapay bir şema örneğiyle erişim testinden geçti; bu finansal kalite ölçümü değildir. Mevcut Codex CLI oturumu kullanılır; doğrudan API fiyatı/kredi tüketimi ölçüldü diye sunulmaz.
