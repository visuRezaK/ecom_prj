# Generated by Django 4.2 on 2025-01-09 00:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0003_order_address'),
    ]

    operations = [
        migrations.RenameField(
            model_name='order',
            old_name='vendor',
            new_name='vendors',
        ),
    ]
