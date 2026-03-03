from django.db import migrations, models
from django.db.models.functions import Lower, Trim


def normalize_and_check_project_titles(apps, schema_editor):
    Project = apps.get_model("pm", "Project")

    seen = {}
    duplicates = []

    for record in Project.objects.all().order_by("id"):
        raw_title = record.project_title or ""
        normalized_title = raw_title.strip()

        if raw_title != normalized_title:
            record.project_title = normalized_title
            record.save(update_fields=["project_title"])

        key = (record.customer_name_id, normalized_title.casefold())
        if key in seen:
            duplicates.append((record.customer_name_id, normalized_title, seen[key], record.id))
        else:
            seen[key] = record.id

    if duplicates:
        duplicate_lines = ", ".join(
            [
                f"client_id={client_id}, project_title='{project_title}' (record ids: {first_id}, {second_id})"
                for client_id, project_title, first_id, second_id in duplicates
            ]
        )
        raise RuntimeError(
            "Cannot enforce unique project titles per client because duplicates already exist: "
            + duplicate_lines
            + ". Please remove or rename duplicate records, then run migrations again."
        )


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("pm", "0003_remove_project_provisioning_form_and_more"),
    ]

    operations = [
        migrations.RunPython(normalize_and_check_project_titles, reverse_noop),
        migrations.AddConstraint(
            model_name="project",
            constraint=models.UniqueConstraint(
                "customer_name",
                Lower(Trim("project_title")),
                name="unique_client_project_title_ci",
            ),
        ),
    ]
