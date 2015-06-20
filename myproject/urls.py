from django.conf.urls import patterns, include, url
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'liarsdice.views.home', name='home'),
    # url(r'^liarsdice/', include('liarsdice.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'login', 'game.views.login_page'),
    url(r'logout', 'game.views.logout_user'),
    url(r'^authenticate_user/$', 'game.views.authenticate_user'),
    url(r'request_game', 'game.views.request_game'),
    url(r'join_game', 'game.views.join_game'),
    url(r'test', 'game.views.test_norefresh'),
    url(r'turncheck', 'game.views.turncheck'),
    url(r'get_opponent_rolls', 'game.views.get_opponent_rolls'),
    url(r'delete_req', 'game.views.delete_request'),
    url(r'create_user', 'game.views.create_user'),
    url(r'^$', 'game.views.main'),
    #chat urls
    #url(r'simple$', 'jchat.views.simple'),
    #url(r'complex/(?P<id>\d)$', 'jchat.views.complex'),
    url(r'send', 'jchat.views.send'),
    url(r'receive', 'jchat.views.receive'),
    url(r'sync', 'jchat.views.sync'),
    url(r'join/', 'jchat.views.join'),
    url(r'leave', 'jchat.views.leave'),
    url(r'chat/', include('jchat.urls')),

     ##following required for serving photos/other media stored in files
     url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
         'document_root': settings.MEDIA_ROOT,
     }),
     url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {
         'document_root': settings.STATIC_ROOT,
     }),
)
