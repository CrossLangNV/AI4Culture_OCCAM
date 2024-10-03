from django.apps import apps
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import (
    UserManager as DjangoUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone


class UserManager(DjangoUserManager):
    def normalize_email(cls, email):
        """
        Normalize the email address by lowercasing it.
        TODO
        """
        email = super().normalize_email(email)
        email_parts = email.split("@")
        email_parts[-1] = email_parts[-1].lower()
        return "@".join(email_parts)

    def _create_user(self, username, email, password, **extra_fields):
        """
        Create and save a user with the given email, and password.
        """

        email = self.normalize_email(email)
        # Lookup the real model class from the global app registry so this
        # manager method can be used in migrations. This is fine because
        # managers are by definition working on the real model.
        GlobalUserModel = apps.get_model(
            self.model._meta.app_label, self.model._meta.object_name
        )

        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        return super().create_user(None, email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        return super().create_superuser(None, email, password, **extra_fields)


class LowercaseEmailField(models.EmailField):
    """
    Override EmailField to convert emails to lowercase before saving.
    """

    def to_python(self, value):
        """
        Convert email to lowercase.
        """
        value = super(LowercaseEmailField, self).to_python(value)
        # Value can be None so check that it's a string before lowercasing.
        if isinstance(value, str):
            return value.lower()
        return value


class User(AbstractBaseUser, PermissionsMixin):
    email = LowercaseEmailField(db_index=True, unique=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created = models.DateTimeField(default=timezone.now)
    updated = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"

    objects = UserManager()

    def __str__(self):
        return f"{self.email}"
