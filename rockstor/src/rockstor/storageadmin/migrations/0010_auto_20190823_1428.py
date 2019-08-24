# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storageadmin', '0009_auto_20190821_0609'),
    ]

    operations = [
        migrations.AlterField(
            model_name='disk',
            name='btrfs_uuid',
            field=models.CharField(max_length=1024, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='disk',
            name='model',
            field=models.CharField(max_length=1024, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='disk',
            name='role',
            field=models.CharField(max_length=1024, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='disk',
            name='serial',
            field=models.CharField(max_length=1024, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='disk',
            name='transport',
            field=models.CharField(max_length=1024, null=True, blank=True),
        ),
    ]
