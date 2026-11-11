# PO Takip Sistemi

[![CI](https://github.com/halilcode/blend_proje/actions/workflows/ci.yml/badge.svg)](https://github.com/halilcode/blend_proje/actions/workflows/ci.yml)

Öğrencilerin **Program Çıktısı (PO)** puanlarını yöneten web tabanlı sistem.
CSE 311 & CSE 321 takım projesi (Güz 2026). Pilot müşteri: Acıbadem CSE.

Puanlar şu sırayla akar: **Not → Öğrenme Çıktısı (LO) → Program Çıktısı (PO)**.
Her adımda kullanılan formül:

```
puan = Σ(ağırlık × puan) ÷ Σ ağırlıklar
```

Ayrıntılar ve ER diyagramı için: [docs/data-model.md](docs/data-model.md) · Canlı demo akışı: [docs/demo.md](docs/demo.md)

## Kurulum

Python 3.12+ gerekir.

```bash
python -m venv .venv
```

```bash
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

```bash
python manage.py migrate
```

```bash
python manage.py seed_demo       # örnek veri (11 PO, CSE 311 örneği, demo kullanıcılar)
```

```bash
python manage.py runserver
```

Sonra http://127.0.0.1:8000 adresini aç.

Demo kullanıcıların hepsinin şifresi `demo12345`:

| Kullanıcı | Rol |
|---|---|
| `admin` | Sistem yöneticisi (yönetim paneli) |
| `bolum_baskani` | Bölüm başkanı (bölümün tüm dersleri) |
| `hoca`, `hoca2` | Öğretim üyesi (yalnızca kendi dersleri) |
| `elif`, `can`, `deniz`, `mert` | Öğrenci (ana sayfada kendi PO profilini görür) |

## Testler

```bash
python manage.py test
```

## Geliştirme süreci

**Branching modeli: GitHub Flow.** Tek uzun ömürlü dal `main`'dir ve her zaman testleri geçen sürümdür. Her iş, `main`'den açılan kısa ömürlü bir dalda yapılır: `feature/…` (yeni özellik), `fix/…` (hata düzeltme), `docs/…` (dokümantasyon). Ayrı bir development, release veya deployment dalı kullanmıyoruz; yayına alma (#20) doğrudan `main`'den yapılacak.

1. `git switch main && git pull`
2. `git switch -c feature/<issue-no>-<kısa-ad>`
3. Küçük, açık mesajlı commit'ler
4. `git push -u origin feature/<issue-no>-<kısa-ad>` ve pull request: ne, neden, nasıl test edilir; açıklamada `Closes #<issue-no>`
5. CI yeşil ve en az bir takım arkadaşı onayladıktan sonra birleştirilir, dal silinir

`main` korumalıdır: doğrudan push ve force-push kapalı, birleştirme için pull request ve 1 onay gerekir.

**Backlog:** GitHub Issues. Her iş bir user story'dir ("As a …, I want …, so that …") ve kabul kriterleri içerir. Sprintler 1 haftadır ve her sprint bir milestone'dur.

**Tahmin: Planning Poker.** Sprint planlamasında her story 1, 3, 5, 8, 13 kartlarıyla puanlanır: herkes kartını gizli seçer, kartlar birlikte açılır. Herkes iki kart aralığındaysa ortalama alınır; daha uzaksa en yüksek ve en düşük kartı açan nedenini anlatır ve yeniden oylanır. Sonuç story'ye `sp: …` etiketi olarak yazılır. 13 puanlık bir story sprinte alınmadan önce bölünür.

**Pano:** GitHub Projects'teki *Blend Sprint Board* (Backlog → To Do → Doing → Done). Bir kart, bitti tanımını karşılamadan Done'a taşınmaz.

**Bitti tanımı (Definition of Done):** kabul kriterleri karşılandı, testleri yazıldı, CI yeşil, pull request onaylandı ve `main`'e birleşti.

## Proje yapısı

```
config/      Django ayarları ve URL'ler
accounts/    Kullanıcı modeli ve roller (admin, bölüm başkanı, öğretim üyesi, öğrenci)
academics/   Bölüm, PO, ders, dönemlik açılış, LO ve LO→PO eşlemeleri
grading/     Değerlendirme, kayıt, not; puan hesaplama (scoring.py)
templates/   HTML şablonları
docs/        Tasarım belgeleri
```

## Ortam değişkenleri

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `DJANGO_SECRET_KEY` | geliştirme anahtarı | Production'da mutlaka ayarlanmalı |
| `DJANGO_DEBUG` | `true` | Production'da `false` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Virgülle ayrılmış liste |
| `DATABASE_ENGINE` | SQLite | `postgresql` verilirse `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` kullanılır |
