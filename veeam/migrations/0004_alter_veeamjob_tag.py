from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("veeam", "0003_veeamjob_engineer"),
    ]

    operations = [
        migrations.AlterField(
            model_name="veeamjob",
            name="tag",
            field=models.CharField(
                blank=True,
                max_length=100,
                verbose_name="Tag",
            ),
        ),
    ]
