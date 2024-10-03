# Generated by Django 4.2 on 2024-04-29 10:27

import django.db.models.deletion
from django.db import migrations, models

import shared.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("organisation", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UsageSegmentation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    shared.models.StatusField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("IN_PROGRESS", "In progress"),
                            ("SUCCESS", "Success"),
                            ("FAILED", "Failed"),
                        ],
                        default="PENDING",
                        max_length=100,
                    ),
                ),
                ("date", models.DateTimeField(auto_now_add=True)),
                (
                    "source_language",
                    models.CharField(blank=True, max_length=10, null=True),
                ),
                ("source_size", models.PositiveIntegerField(blank=True, null=True)),
                ("target_size", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "api_key",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="organisation.organisationapikey",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
