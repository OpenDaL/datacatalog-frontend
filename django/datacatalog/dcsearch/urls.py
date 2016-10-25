# -*- coding: utf-8 -*-
from django.contrib.sitemaps.views import sitemap
from django.urls import path

from . import views
from .sitemaps import StaticViewSitemap

sitemaps = {
    'static': StaticViewSitemap,
}

app_name = 'dcsearch'
urlpatterns = [
    path('', views.search, name='search'),
    path('resource/<resource_id>/', views.get_resource, name='resource_page'),
    path('components/results/', views.result_list, name='result_list'),
    path('components/aggregations/', views.aggregations, name='aggregations'),
    path('search/components/', views.search_components, name='search_components'),
    path('about/', views.get_static_page,
         kwargs={'page_id': 'about'}, name='about'),
    path('support/', views.get_static_page,
         kwargs={'page_id': 'support'}, name='support'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps},
         name='django.contrib.sitemaps.views.sitemap')
]
