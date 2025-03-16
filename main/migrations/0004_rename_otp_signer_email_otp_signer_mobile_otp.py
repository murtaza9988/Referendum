# Generated by Django 5.1.7 on 2025-03-16 05:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_signer_otp_signer_otp_created_at'),
    ]

    operations = [
        migrations.RenameField(
            model_name='signer',
            old_name='otp',
            new_name='email_otp',
        ),
        migrations.AddField(
            model_name='signer',
            name='mobile_otp',
            field=models.CharField(blank=True, max_length=6, null=True),
        ),
    ]
