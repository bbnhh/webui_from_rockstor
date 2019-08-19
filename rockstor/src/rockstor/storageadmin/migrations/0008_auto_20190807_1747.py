# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storageadmin', '0007_auto_20181210_0740'),
    ]

    operations = [
        migrations.AddField(
            model_name='share',
            name='poolname',
            field=models.CharField(max_length=4096, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='share',
            name='pqgroup',
            field=models.CharField(default=b'-1/-1', max_length=32, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='share',
            name='qgroup',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='share',
            name='uuid',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
    ]
