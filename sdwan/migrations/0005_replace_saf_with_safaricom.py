from django.db import migrations


def replace_saf_with_safaricom(apps, schema_editor):
    SDWAN = apps.get_model("sdwan", "SDWAN")

    for record in SDWAN.objects.all().only("id", "providers"):
        providers = record.providers or []
        updated = ["Safaricom" if value == "Saf" else value for value in providers]
        if updated != providers:
            record.providers = updated
            record.save(update_fields=["providers"])


def revert_to_saf(apps, schema_editor):
    SDWAN = apps.get_model("sdwan", "SDWAN")

    for record in SDWAN.objects.all().only("id", "providers"):
        providers = record.providers or []
        updated = ["Saf" if value == "Safaricom" else value for value in providers]
        if updated != providers:
            record.providers = updated
            record.save(update_fields=["providers"])


class Migration(migrations.Migration):

    dependencies = [
        ("sdwan", "0004_remove_sdwan_sdwan_sdwan_provide_0c60b0_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(replace_saf_with_safaricom, revert_to_saf),
    ]
