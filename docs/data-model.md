# Veri Modeli

Puanlar üç adımda akar: **Not → Öğrenme Çıktısı (LO) → Program Çıktısı (PO)**.
Her adımda formül aynıdır: `puan = Σ(ağırlık × puan) ÷ Σ ağırlıklar`.

## ER diyagramı

```mermaid
erDiagram
    Department ||--o{ ProgramOutcome : "tanımlar"
    Department ||--o{ Course : "açar"
    Department ||--o{ User : "üyesi"
    User |o--o{ Department : "başkanı (head)"

    Course ||--o{ LearningOutcome : "izlencesinde"
    Course ||--o{ CourseContribution : ""
    ProgramOutcome ||--o{ CourseContribution : "1-5 katkı"
    LearningOutcome ||--o{ LearningOutcomeMapping : ""
    ProgramOutcome ||--o{ LearningOutcomeMapping : "% ağırlık"

    Course ||--o{ CourseOffering : "dönemlik açılış"
    CourseOffering }o--o{ User : "öğretim üyeleri"
    CourseOffering ||--o{ Assessment : ""
    Assessment ||--o{ AssessmentMapping : ""
    LearningOutcome ||--o{ AssessmentMapping : "% ağırlık"

    User ||--o{ Enrollment : "öğrenci"
    CourseOffering ||--o{ Enrollment : ""
    Enrollment ||--o{ Grade : ""
    Assessment ||--o{ Grade : ""

    User {
        bigint id PK
        string username
        string role "admin | department_head | instructor | student"
        bigint department_id FK
        string student_number "UNIQUE, NULL"
    }
    Department {
        bigint id PK
        string code "UNIQUE"
        string name
        bigint head_id FK
    }
    ProgramOutcome {
        bigint id PK
        bigint department_id FK
        smallint number "UNIQUE(department, number)"
        string short_name
        text description
    }
    Course {
        bigint id PK
        bigint department_id FK
        string code "UNIQUE"
        string name
        smallint credits
        smallint ects
    }
    CourseContribution {
        bigint id PK
        bigint course_id FK
        bigint program_outcome_id FK
        smallint level "1-5"
    }
    CourseOffering {
        bigint id PK
        bigint course_id FK
        smallint year
        string semester "fall | spring | summer"
        smallint section
    }
    LearningOutcome {
        bigint id PK
        bigint course_id FK
        smallint number "UNIQUE(course, number)"
        text description
    }
    LearningOutcomeMapping {
        bigint id PK
        bigint learning_outcome_id FK
        bigint program_outcome_id FK
        decimal weight "0-100"
    }
    Assessment {
        bigint id PK
        bigint offering_id FK
        string name
        string kind "midterm | final | project | ..."
        decimal max_score
        date date
    }
    AssessmentMapping {
        bigint id PK
        bigint assessment_id FK
        bigint learning_outcome_id FK
        decimal weight "0-100"
    }
    Enrollment {
        bigint id PK
        bigint student_id FK
        bigint offering_id FK
        datetime enrolled_at
    }
    Grade {
        bigint id PK
        bigint enrollment_id FK
        bigint assessment_id FK
        decimal score ">= 0"
        bigint entered_by_id FK
        datetime updated_at
    }
```

## Tasarım kararları

| Karar | Neden |
|---|---|
| **LO'lar `Course`'a, değerlendirmeler `CourseOffering`'e bağlı** | Öğrenme çıktıları izlencede tanımlanır ve dönemden döneme pek değişmez. Sınavlar ve notlar ise her dönem farklıdır. |
| **İki ayrı ağırlık türü** | `LearningOutcomeMapping.weight` (%) LO'ların ders içinde PO'ya nasıl aktığını belirler. `CourseContribution.level` (1–5) ise derslerin öğrencinin genel PO profilinde ne kadar sayılacağını belirler. |
| **Notlar 0–100'e normalize edilir** | 20 puanlık bir quiz ile 100 puanlık bir sınav aynı formülde birleştirilebilsin diye. |
| **Girilmemiş not 0 sayılmaz** | Henüz notu girilmemiş değerlendirmeler hesaba katılmaz. Böylece dönem ortasında puanlar haksız yere düşmez. |
| **Kısıtlar veritabanında** | `UNIQUE` ve `CHECK` kısıtları (ağırlık 0–100, katkı 1–5, not ≥ 0) uygulama hatası olsa bile veriyi tutarlı tutar. |
| **Puanlar saklanmıyor, hesaplanıyor** | Şimdilik puanlar her istekte hesaplanıyor (`grading/scoring.py`). Veri büyüyünce önbellek veya materialized view eklenebilir. |

## Diyagram dosyaları

| Diyagram | Kaynak (Mermaid) | Görsel |
|---|---|---|
| Sistem mimarisi | [diagrams/architecture.mmd](diagrams/architecture.mmd) | [img/architecture.svg](img/architecture.svg) |
| Sınıf diyagramı | [diagrams/class-diagram.mmd](diagrams/class-diagram.mmd) | [img/class-diagram.svg](img/class-diagram.svg) |
| ER diyagramı | [diagrams/data-model.mmd](diagrams/data-model.mmd) | [img/data-model.svg](img/data-model.svg) |

Mimari diyagramında kesik çerçeveli kutular planlanan, düz çerçeveliler bugün kodda olan bileşenlerdir.
