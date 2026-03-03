from django.db import migrations


def forward_noop(apps, schema_editor):
    pass


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("threecx", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forward_noop, reverse_noop),
    ]
