# PO Takip Sistemi

[![CI](https://github.com/halilcode/blend_proje/actions/workflows/ci.yml/badge.svg)](https://github.com/halilcode/blend_proje/actions/workflows/ci.yml)

Öğrencilerin **Program Çıktısı (PO)** puanlarını yöneten web tabanlı sistem.
CSE 311 & CSE 321 takım projesi (Güz 2026). Pilot müşteri: Acıbadem CSE.

Puanlar şu sırayla akar: **Not → Öğrenme Çıktısı (LO) → Program Çıktısı (PO)**.
Her adımda kullanılan formül:

```
puan = Σ(ağırlık × puan) ÷ Σ ağırlıklar
```

Ayrıntılar ve ER diyagramı için: [docs/data-model.md](docs/data-model.md)

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
| `bolum_baskani` | Bölüm başkanı |
| `hoca` | Öğretim üyesi |
| `elif` | Öğrenci (ana sayfada PO profilini görür) |

## Testler

```bash
python manage.py test
```

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
