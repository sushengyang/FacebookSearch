from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'facebook_search.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^facebook/', include('django_facebook.urls')),
	url(r'^accounts/', include('django_facebook.auth_urls')),	
)    
urlpatterns += patterns(
    'search.views',
    url(r'^connect/$', 'connect', name='facebook_connect'),
    url(r'^disconnect/$', 'disconnect', name='facebook_disconnect'),
    url(r'^example/$', 'example', name='facebook_example'),
    url(r'^reindex/$', 'reindex', name='reindex'),
    url(r'^query/$', 'query', name='query'),
)
