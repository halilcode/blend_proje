from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """A system user. Every user has exactly one role."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Sistem Yöneticisi"
        DEPARTMENT_HEAD = "department_head", "Bölüm Başkanı"
        INSTRUCTOR = "instructor", "Öğretim Üyesi"
        STUDENT = "student", "Öğrenci"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    department = models.ForeignKey(
        "academics.Department",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="members",
    )
    # Only meaningful for students; unique when present.
    student_number = models.CharField(max_length=20, unique=True, null=True, blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        full_name = self.get_full_name()
        return full_name or self.username

    def save(self, *args, **kwargs):
        # Forms submit "" for an empty field; store NULL so the unique constraint
        # does not treat every non-student as a duplicate.
        if not self.student_number:
            self.student_number = None
        super().save(*args, **kwargs)

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_instructor(self):
        return self.role == self.Role.INSTRUCTOR

    @property
    def is_department_head(self):
        return self.role == self.Role.DEPARTMENT_HEAD
