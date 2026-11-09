from django.contrib.auth.models import AbstractUser, UserManager as BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # User.save() derives is_staff/is_superuser from the role, so a superuser
        # left with the default "student" role would be stripped of admin access.
        extra_fields.setdefault("role", User.Role.ADMIN)
        if extra_fields["role"] != User.Role.ADMIN:
            raise ValueError("Süper kullanıcının rolü 'admin' olmalıdır.")
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """A system user. Every user has exactly one role."""

    objects = UserManager()

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

        if self.role == self.Role.STUDENT:
            self.is_staff = False
            self.is_superuser = False
        elif self.role == self.Role.ADMIN:
            self.is_staff = True
            self.is_superuser = True
        else:
            self.is_staff = True

        super().save(*args, **kwargs)
        self.sync_role_group()

    def sync_role_group(self):
        from .permissions import sync_user_groups
        sync_user_groups(self)

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_instructor(self):
        return self.role == self.Role.INSTRUCTOR

    @property
    def is_department_head(self):
        return self.role == self.Role.DEPARTMENT_HEAD
