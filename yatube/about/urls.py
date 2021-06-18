from django.urls import path

from . import views

app_name = 'about'

urlpatterns = [path("tech/", views.about_tech_view.as_view(), name="tech"),
               path("author/",
               views.about_author_view.as_view(),
               name="author")
               ]
