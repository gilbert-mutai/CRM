from django.db import migrations, models


def check_duplicate_threecx_clients(apps, schema_editor):
    ThreeCX = apps.get_model("threecx", "ThreeCX")

    seen = {}
    duplicates = []

    for record in ThreeCX.objects.all().order_by("id"):
        client_id = record.client_id
        if client_id in seen:
            duplicates.append((client_id, seen[client_id], record.id))
        else:
            seen[client_id] = record.id

    if duplicates:
        duplicate_lines = ", ".join(
            [
                f"client_id={client_id} (record ids: {first_id}, {second_id})"
                for client_id, first_id, second_id in duplicates
            ]
        )
        raise RuntimeError(
            "Cannot enforce unique 3CX records per client because duplicates already exist: "
            + duplicate_lines
            + ". Please remove or reassign duplicate records, then run migrations again."
        )


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("threecx", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(check_duplicate_threecx_clients, reverse_noop),
        migrations.AddConstraint(
            model_name="threecx",
            constraint=models.UniqueConstraint(
                fields=["client"],
                name="unique_threecx_client",
            ),
        ),
    ]
