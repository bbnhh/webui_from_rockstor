"""
Copyright (c) 2012-2016 RockStor, Inc. <http://rockstor.com>
This file is part of RockStor.

RockStor is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published
by the Free Software Foundation; either version 2 of the License,
or (at your option) any later version.

RockStor is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

from django.db import models
from django.conf import settings
from fs.btrfs import pool_usage, usage_bound, \
    are_quotas_enabled, is_pool_missing_dev, dev_stats_zero
from system.osi import mount_status
import logging
RETURN_BOOLEAN = True


class Pool(models.Model):
    """Name of the pool"""
    name = models.CharField(max_length=4096, unique=True)
    """uuid given automatically by the client"""
    uuid = models.CharField(max_length=100, null=True)
    """size of the pool in KB"""
    size = models.BigIntegerField(default=0)
    raid = models.CharField(max_length=10)
    toc = models.DateTimeField(auto_now=True)
    compression = models.CharField(max_length=256, null=True)
    mnt_options = models.CharField(max_length=4096, null=True)
    """optional aux info. eg: role = root for OS Pool"""
    role = models.CharField(max_length=256, null=True)
    health = models.CharField(max_length=256, null=True)

    def __init__(self, *args, **kwargs):
        super(Pool, self).__init__(*args, **kwargs)
        self.update_missing_dev()
        self.update_device_stats()

    def update_missing_dev(self, *args, **kwargs):
        # Establish an instance variable to track missing device status.
        # Currently Boolean and may be updated during instance life by
        # calling this method again or directly setting the field.
        try:
            self.missing_dev = is_pool_missing_dev(self.name)
        except:
            self.missing_dev = False

    @property
    def has_missing_dev(self, *args, **kwargs):
        return self.missing_dev

    def update_device_stats(self, *args, **kwargs):
        # Establish an instance variable to represent non zero stats.
        # Currently Boolean and may be updated during instance life by
        # calling this method again or directly setting the field.
        try:
            if self.is_mounted:
                mnt_pt = '%s%s' % (settings.MNT_PT, self.name)
                self.dev_stats_zero = dev_stats_zero(mnt_pt)
            else:
                self.dev_stats_zero = True
        except:
            self.dev_stats_zero = True

    @property
    def dev_stats_ok(self, *args, **kwargs):
        return self.dev_stats_zero

    @property
    def free(self, *args, **kwargs):
        # Why do we compute pool usage on the fly like this and not like
        # share usage as part of state refresh? This is a lot simpler and
        # less code. For share usage, this type of logic could slow things
        # down quite a bit because there can be 100's of Shares, but number
        # of Pools even on a large instance is usually no more than a few.
        #return self.size - pool_usage('%s%s' % (settings.MNT_PT, self.name))
        logger = logging.getLogger(__name__)
        s = pool_usage('%s' % (self.name))
        #logger.debug("POOLLLLLL")
        #logger.debug(s)
        return pool_usage('%s' % (self.name))

    @property
    def reclaimable(self, *args, **kwargs):
        return 0

    def usage_bound(self):
        disk_sizes = [int(size) for size in self.disk_set
                      .values_list('size', flat=True)
                      .order_by('-size')]
        return usage_bound(disk_sizes, len(disk_sizes), self.raid)

    @property
    def mount_status(self, *args, **kwargs):
        # Presents raw string of active mount options akin to mnt_options field
        try:
            return mount_status('%s%s' % (settings.MNT_PT, self.name))
        except:
            return None

    @property
    def is_mounted(self, *args, **kwargs):
        # Calls mount_status in return boolean mode.
        try:
            return mount_status('%s%s' % (settings.MNT_PT, self.name),
                                RETURN_BOOLEAN)
        except:
            return False

    @property
    def quotas_enabled(self, *args, **kwargs):
        # Calls are_quotas_enabled for boolean response
        try:
            return are_quotas_enabled('%s%s' % (settings.MNT_PT, self.name))
        except:
            return False

    class Meta:
        app_label = 'storageadmin'
