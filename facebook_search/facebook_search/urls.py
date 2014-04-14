from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^facebook/', include('django_facebook.urls')),
	url(r'^accounts/', include('django_facebook.auth_urls')),	
)    
urlpatterns += patterns(
    'search.views',
    url(r'^connect/$', 'connect', name='facebook_connect'),
    url(r'^disconnect/$', 'disconnect', name='facebook_disconnect'),
    url(r'^$', 'index', name='index'),
    url(r'^logout/$', 'logout', name='logout'),
    url(r'^reindex/$', 'reindex', name='reindex'),
    url(r'^query/$', 'query', name='query'),
    url(r'^profile-picture/$', 'getProfilePicture', name='profile_picture'),
    url(r'^graph-post/(?P<postID>[0-9_]+)/$', 'getGraphPost', name='graph_post'),
	url(r'^inverted-index/(?P<userID>\d+)/$', 'getInvertedIndex', name='inverted_index'),
)
