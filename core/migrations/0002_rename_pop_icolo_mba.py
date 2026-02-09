from django.db import migrations


OLD_VALUE = "Icolo MBO"
NEW_VALUE = "Icolo MBA"


def _replace_pop_value(pop_string, old_value, new_value):
    if not pop_string:
        return pop_string
    parts = [p.strip() for p in pop_string.split(",") if p.strip()]
    updated = [new_value if p == old_value else p for p in parts]
    return ",".join(updated)


def forwards(apps, schema_editor):
    Client = apps.get_model("core", "Client")
    for client in Client.objects.all():
        updated = _replace_pop_value(client.point_of_presence, OLD_VALUE, NEW_VALUE)
        if updated != client.point_of_presence:
            client.point_of_presence = updated
            client.save(update_fields=["point_of_presence"])


def backwards(apps, schema_editor):
    Client = apps.get_model("core", "Client")
    for client in Client.objects.all():
        updated = _replace_pop_value(client.point_of_presence, NEW_VALUE, OLD_VALUE)
        if updated != client.point_of_presence:
            client.point_of_presence = updated
            client.save(update_fields=["point_of_presence"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
