from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("veeam", "0002_enforce_unique_client_computer_name_ci"),
    ]

    operations = [
        migrations.AddField(
            model_name="veeamjob",
            name="engineer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="veeam_jobs",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Engineer",
                limit_choices_to={"groups__name": "Engineers"},
            ),
        ),
    ]
