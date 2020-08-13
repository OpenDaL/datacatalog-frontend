# -*- coding: utf-8 -*-
"""
Defines the basic sitemap
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
                'lastmod': datetime.datetime(2020, 8, 13),
                'changefreq': 'weekly'
            },
            {
                'name': 'support',
                'priority': 0.3,
                'lastmod': datetime.datetime(2020, 7, 10),
                'changefreq': 'monthly'
            },
            {
                'name': 'about',
                'priority': 0.6,
                'lastmod': datetime.datetime(2020, 7, 10),
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
