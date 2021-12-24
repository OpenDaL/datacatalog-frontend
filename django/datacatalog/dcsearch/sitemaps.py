# -*- coding: utf-8 -*-
"""
Defines the basic sitemap

Copyright (C) 2021  Tom Brouwer

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import datetime

from django.contrib import sitemaps
from django.urls import reverse


class StaticViewSitemap(sitemaps.Sitemap):
    def items(self):
        return [
            {
                'name': 'search',
                'priority': 1.0,
                'lastmod': datetime.datetime(2021, 12, 10),
                'changefreq': 'weekly'
            },
            {
                'name': 'support',
                'priority': 0.3,
                'lastmod': datetime.datetime(2021, 12, 10),
                'changefreq': 'monthly'
            },
            {
                'name': 'about',
                'priority': 0.6,
                'lastmod': datetime.datetime(2021, 12, 10),
                'changefreq': 'monthly'
            },
        ]

    def location(self, item):
        uid = 'dcsearch:' + item['name']
        return reverse(uid)

    def lastmod(self, item):
        return item['lastmod']

    def priority(self, item):
        return item['priority']

    def changefreq(self, item):
        return item['changefreq']
