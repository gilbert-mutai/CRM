from django.db import migrations, models
from django.db.models.functions import Lower, Trim


def normalize_and_check_sdwan_accounts(apps, schema_editor):
    SDWAN = apps.get_model("sdwan", "SDWAN")

    seen = {}
    duplicates = []

    for record in SDWAN.objects.all().order_by("id"):
        raw_account = record.account_number or ""
        normalized_account = raw_account.strip()

        if raw_account != normalized_account:
            record.account_number = normalized_account
            record.save(update_fields=["account_number"])

        key = (record.client_id, normalized_account.casefold())
        if key in seen:
            duplicates.append((record.client_id, normalized_account, seen[key], record.id))
        else:
            seen[key] = record.id

    if duplicates:
        duplicate_lines = ", ".join(
            [
                f"client_id={client_id}, account='{account}' (record ids: {first_id}, {second_id})"
                for client_id, account, first_id, second_id in duplicates
            ]
        )
        raise RuntimeError(
            "Cannot enforce unique SD-WAN account numbers per client because duplicates already exist: "
            + duplicate_lines
            + ". Please remove or edit duplicate records, then run migrations again."
        )


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("sdwan", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(normalize_and_check_sdwan_accounts, reverse_noop),
        migrations.RemoveConstraint(
            model_name="sdwan",
            name="unique_client_account_number",
        ),
        migrations.AddConstraint(
            model_name="sdwan",
            constraint=models.UniqueConstraint(
                "client",
                Lower(Trim("account_number")),
                name="unique_client_account_number_ci",
            ),
        ),
    ]
