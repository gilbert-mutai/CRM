from django.db import migrations, models
from django.db.models.functions import Lower, Trim


def normalize_and_check_client_names(apps, schema_editor):
    Client = apps.get_model("core", "Client")

    seen = {}
    duplicates = []

    for client in Client.objects.all().order_by("id"):
        raw_name = client.name or ""
        normalized_name = raw_name.strip()
        key = normalized_name.casefold()

        if raw_name != normalized_name:
            client.name = normalized_name
            client.save(update_fields=["name"])

        if key in seen:
            duplicates.append((normalized_name, seen[key], client.id))
        else:
            seen[key] = client.id

    if duplicates:
        duplicate_lines = ", ".join(
            [
                f"'{name}' (ids: {first_id}, {second_id})"
                for name, first_id, second_id in duplicates
            ]
        )
        raise RuntimeError(
            "Cannot enforce unique client names because duplicates already exist: "
            + duplicate_lines
            + ". Please remove or rename duplicates, then run migrations again."
        )


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_rename_pop_icolo_mba"),
    ]

    operations = [
        migrations.RunPython(normalize_and_check_client_names, reverse_noop),
        migrations.RemoveConstraint(
            model_name="client",
            name="unique_client_name_email",
        ),
        migrations.AddConstraint(
            model_name="client",
            constraint=models.UniqueConstraint(
                Lower(Trim("name")),
                name="unique_client_name_ci",
            ),
        ),
    ]
