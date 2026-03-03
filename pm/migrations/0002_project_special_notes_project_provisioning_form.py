from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("pm", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="special_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="project",
            name="provisioning_form",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="pm/provisioning_forms/",
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=[
                            "pdf",
                            "doc",
                            "docx",
                            "png",
                            "jpg",
                            "jpeg",
                            "gif",
                            "webp",
                        ]
                    )
                ],
            ),
        ),
    ]
