from django.db import migrations


def normalize_project_titles(apps, schema_editor):
    Project = apps.get_model("pm", "Project")

    for record in Project.objects.all().order_by("id"):
        raw_title = record.project_title or ""
        normalized_title = raw_title.strip()

        if raw_title != normalized_title:
            record.project_title = normalized_title
            record.save(update_fields=["project_title"])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("pm", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(normalize_project_titles, reverse_noop),
    ]
