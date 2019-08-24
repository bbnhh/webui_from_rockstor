# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storageadmin', '0008_auto_20190807_1747'),
    ]

    operations = [
        migrations.AlterField(
            model_name='snapshot',
            name='qgroup',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
    ]
