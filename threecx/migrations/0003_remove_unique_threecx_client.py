from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("threecx", "0002_enforce_unique_threecx_client"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE threecx_threecx DROP CONSTRAINT IF EXISTS unique_threecx_client;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
