from django.db import migrations, models
from django.db.models.functions import Lower, Trim


def normalize_and_check_veeam_computer_names(apps, schema_editor):
    VeeamJob = apps.get_model("veeam", "VeeamJob")

    seen = {}
    duplicates = []

    for record in VeeamJob.objects.all().order_by("id"):
        raw_name = record.computer_name or ""
        normalized_name = raw_name.strip()

        if raw_name != normalized_name:
            record.computer_name = normalized_name
            record.save(update_fields=["computer_name"])

        key = (record.client_id, normalized_name.casefold())
        if key in seen:
            duplicates.append((record.client_id, normalized_name, seen[key], record.id))
        else:
            seen[key] = record.id

    if duplicates:
        duplicate_lines = ", ".join(
            [
                f"client_id={client_id}, computer_name='{computer_name}' (record ids: {first_id}, {second_id})"
                for client_id, computer_name, first_id, second_id in duplicates
            ]
        )
        raise RuntimeError(
            "Cannot enforce unique Veeam computer names per client because duplicates already exist: "
            + duplicate_lines
            + ". Please remove or edit duplicate records, then run migrations again."
        )


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("veeam", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(normalize_and_check_veeam_computer_names, reverse_noop),
        migrations.RemoveConstraint(
            model_name="veeamjob",
            name="unique_client_computer_ci",
        ),
        migrations.AddConstraint(
            model_name="veeamjob",
            constraint=models.UniqueConstraint(
                "client",
                Lower(Trim("computer_name")),
                name="unique_client_computer_ci",
            ),
        ),
    ]
