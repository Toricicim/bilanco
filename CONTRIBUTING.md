# Ekip için GitHub rehberi

Güncelleme: 24 Ekim 2026. Bu kurallar ekip üyeleri ve onların AI ajanları için aynıdır.

**`main`e doğrudan commit veya push atılmaz. Her bağımsız yenilik, düzeltme veya doküman işi ayrı branch'te yapılır ve pull request (PR) ile sunulur.** PR açmak değişikliği `main`e eklemez; inceleme ve birleştirme ayrı adımdır.

## 1. Kavramlar

- **Repository (repo):** Kodun ve değişiklik geçmişinin tutulduğu proje.
- **Branch:** Bir işi ana koddan ayrı geliştirdiğin dal. Örneğin `feat/kap-okuyucu`.
- **Commit:** Yaptığın değişikliğin yerel kayıt noktası. Her commit tek anlaşılır değişiklik anlatsın.
- **Push:** Branch'indeki commit'leri GitHub'a gönderir.
- **Pull request:** Branch'inin `main`e eklenmesi için inceleme talebi.
- **Merge:** İncelenen PR'ın ana koda alınması. Ajanlar kendiliğinden merge etmez.

## 2. İlk kez indirme

```sh
git clone https://github.com/Toricicim/bilanco.git
cd bilanco
```

GitHub'a yazma yetkin varsa aşağıdaki ortak repo akışını kullan. Yetkin yoksa GitHub'da **Fork** oluştur; kendi kopyanı klonla, branch'ini kendi `origin` adresine pushla ve PR hedefini `Toricicim/bilanco:main` seç. Kimsenin oturumunu veya parolasını paylaşma.

Programı kurmak için [README](README.md) adımlarını izle. Herkes kendi `.env`, veritabanı ve Codex oturumunu kullanır. Yerel analiz verileri Git ile gelmez.

## 3. Her yeni işe başlarken

Önce çalışma klasörünü kontrol et:

```sh
git status --short
git branch --show-current
git fetch origin
```

İlk komut çıktı veriyorsa kaydedilmemiş değişiklik vardır. Bunları silme, `reset --hard` çalıştırma ve başka işle karıştırma. Önce ilgili branch'te kayıt altına al veya ayrı worktree kullan. Çalışma alanı temizken **yeni branch'i güncel `origin/main`den** oluştur:

```sh
git switch -c feat/kisa-is-adi origin/main
```

`kisa-is-adi` yerine kendi işini yaz. Branch adları küçük harf ve tire içersin:

| İş | Örnek branch |
| --- | --- |
| Yeni özellik | `feat/kap-tarih-kontrolu` |
| Hata düzeltme | `fix/nakit-isareti` |
| Doküman | `docs/kurulum-rehberi` |
| Kod düzenleme | `refactor/kaynak-okuyucu` |

Aynı yeniliğin düzeltmeleri aynı branch/PR'da kalır. İlgisiz yeni işi o branch'e ekleme; yeni branch aç. Henüz merge edilmemiş başka bir işe bağımlılık varsa PR açıklamasında belirt; o kodu yanlışlıkla kendi işin gibi taşıma.

## 4. Kodla, kontrol et, commit at

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest -q

git diff
```

Testler yapay veri kullanır. Canlı analiz komutunu test yerine çalıştırma. PostgreSQL entegrasyon testleri için README'deki `bilanco_test_` veritabanı adımlarını kullan; kendi analiz veritabanını testlere bağlama. Yalnız doküman değiştiyse bağlantı/komut/diff kontrolü yeterlidir; çalıştırmadığın testi geçti diye yazma.

Commit öncesi doğru branch'te olduğunu kontrol et. **Çıktı `main` ise commit atma.**

```sh
git branch --show-current
git add degistirdigin/dosya.py tests/ilgili_test.py
git diff --cached --stat
git diff --cached
git commit -m "KAP yayın tarihi doğrulamasını düzelt"
```

Örnekteki dosya adlarını kendi dosyalarınla değiştir. `git add .` yerine ilgili yolları tek tek seç; başka kişinin çalışması veya yerel veri yanlışlıkla dahil olmasın. `.env`, parolalar, API anahtarları, Codex kimlik dosyaları, veritabanı yedekleri ve yeni `data/` çıktıları commit edilmez. Paylaşılacak sabit demo ancak ayrıca istenmişse eklenir.

## 5. Branch'i gönder ve PR aç

```sh
git push -u origin feat/kisa-is-adi
```

GitHub'da **Compare & pull request** seç. `base: main`, `compare: kendi-branchin` olmalı. Başlığa yaptığı işi yaz. Açıklamada şunlar bulunsun:

- Hangi sorun çözüldü, kullanıcı davranışı nasıl değişti?
- Hangi testler/kontroller gerçekten çalıştırıldı?
- Kalan eksik veya sonuçları etkileyen sınırlama var mı?

GitHub CLI kullanıyorsan, açıklamayı gerçek satır sonlarıyla bir dosyaya yazıp şu şekilde açabilirsin:

```sh
gh pr create --base main --head feat/kisa-is-adi \
  --title "KAP yayın tarihi doğrulamasını düzelt" --body-file /tmp/bilanco-pr.md
```

`/tmp/bilanco-pr.md` dosyasını önce oluştur. Henüz bitmemiş işte `--draft` kullan. PR şablonu `main`e merge edildikten sonra yeni PR'larda otomatik görünür.

PR'ı bir ekip arkadaşın incelesin; **Checks / test** kontrolünü ve yorumları takip et. PR'da düzeltme istenirse aynı branch'te değiştir, test et, commit ve normal push yap: PR kendiliğinden güncellenir. Kontrol hatasını gizlemek için test silme veya CI kapatma.

**Merge yetkisi proje sorumlusundadır. Ajan görevinin bittiğini PR bağlantısıyla bildirir; açık talimat olmadan merge veya auto-merge açmaz.**

## 6. Ana kod değiştiyse

Kendi branch'inde ve çalışma alanın temizken:

```sh
git fetch origin
git merge origin/main
```

Çakışma varsa dosyadaki iki değişikliğin amacını anlayarak çöz; başkasının kodunu topluca silme. Çözdüğün dosyaları `git add` ile ekle, merge commit'ini tamamla, testleri çalıştır ve kendi branch'ini pushla. Çözümü anlayamadıysan `git merge --abort` ile bu birleştirme denemesinden çıkabilirsin. Bu komutlardan önce çalışma alanının temiz olması önemlidir.

Paylaşılan branch'te geçmişi yeniden yazma, `push --force` veya `push --force-with-lease` kullanma. Bu ekip akışı normal push ile yürür.

PR merge edildikten sonra, temiz çalışma alanında:

```sh
git switch main
git pull --ff-only origin main
```

Burada yeni commit oluşturulmaz; yerel `main` güncellenir. Sonraki iş için yine yeni branch aç. `--ff-only` hata verirse zorlayarak sıfırlama; yereldeki farklı commit'leri kontrol et.

## 7. Yanlışlıkla main üzerinde çalıştıysan

**Henüz commit atmadıysan:** değişikliklerini koruyarak bir branch aç:

```sh
git switch -c fix/degisikligi-tasi
```

Sonra normal kontrol/commit/PR akışına devam et. **Commit attıysan ama pushlamadıysan:** önce aynı şekilde bir branch açarak commit'i koru; `main`e push yapma. Yerel `main`i onarmadan önce hangi commit'lerin farklı olduğunu kontrol et; körlemesine reset yapma. **Main'e pushlandıysa:** geçmişi force push ile değiştirme; proje sorumlusuna bildir, düzeltmeyi PR ile ele alın.

## 8. Ajanına verebileceğin kısa talimat

> Önce AGENTS.md, CONTRIBUTING.md ve README.md dosyalarını oku. Git durumunu kontrol et. Main'e commit/push atma. Bu iş için güncel origin/main'den ayrı branch aç; mevcut kullanıcı değişikliklerini koru. Yalnız görev kapsamını değiştir, ilgili testleri çalıştır. Sırları ve yerel analiz verilerini commit etme. Kendi branch'ini pushla ve main hedefli PR aç. PR'ı merge etme; sonuç, testler ve PR bağlantısını bildir.

Birden çok ajan aynı anda çalışıyorsa aynı çalışma klasöründe branch değiştirmesinler. Her bağımsız iş için ayrı worktree/checkout kullanılsın. Bu, ajan çalıştırma talimatı değildir; eşzamanlı çalışma varsa uygulanır.

## GitHub'da kuralı teknik olarak zorunlu kılmak

Bu rehber ve AGENTS.md çalışma kuralıdır; tek başına sunucuda push engellemez. Yönetici, repo **Settings → Branches → Add classic branch protection rule** bölümünde `main` için PR zorunluluğu, en az bir inceleme onayı, başarılı **test** kontrolü ve çözülmüş konuşmalar şartı koyabilir. Bypass'a izin verilmemeli; force push ve branch silme kapalı kalmalıdır. Gerekli kontrol adını bu reponun son CI kaydından seçin. Bu doküman eklenirken sunucu koruma ayarları değiştirilmedi.

Resmî kaynaklar (24 Ekim 2026): [Korumalı branch'ler](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches), [koruma kuralı oluşturma](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule), [PR şablonları](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/about-issue-and-pull-request-templates).
