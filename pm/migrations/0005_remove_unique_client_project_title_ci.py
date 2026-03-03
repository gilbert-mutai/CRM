from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("pm", "0004_enforce_unique_client_project_title_ci"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE pm_project DROP CONSTRAINT IF EXISTS unique_client_project_title_ci;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
