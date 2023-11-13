# megamicros_aidb/apps/aidb/aidb/urls.py
#
# Copyright (c) 2023 Sorbonne Université
# Author: bruno.gas@sorbonne-universite.fr
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
MegaMicros documentation is available on https://readthedoc.biimea.io

aidb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from megamicros.aidb import views

"""
in .vscode/settings.json :
{
    "python.analysis.extraPaths": [
        "./src/megamicros_aidb/apps/aidb"
    ]
}
"""


"""
urlpatterns = [
    path('admin/', admin.site.urls),
]
"""

router = routers.DefaultRouter()
router.register( r'config', views.ConfigViewSet )
router.register( r'domain', views.DomainViewSet )
router.register( r'campaign', views.CampaignViewSet )
router.register( r'device', views.DeviceViewSet )
router.register( r'directory', views.DirectoryViewSet )
router.register( r'sourcefile', views.SourceFileViewSet )
router.register( r'tagcat', views.TagcatViewSet )
router.register( r'tag', views.TagViewSet )
router.register( r'context', views.ContextViewset )
router.register( r'filecontexting', views.FileContextingViewset )
router.register( r'label', views.LabelViewset )
router.register( r'filelabeling', views.FileLabelingViewset )
router.register( r'dataset', views.DatasetViewSet )


# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('dj-rest-auth/', include('dj_rest_auth.urls'))
    #path('sourcefile/<int:pk>/wav/', views.SourceFileWavView.as_view()),
    #path('sourcefile/wav/', views.SourceFileWavView.as_view()),
]

