from django.urls import path
import views

urlpatterns = [
    path("", views.index, name="home"),
    path("qidiruv/", views.qidiruv, name="qidiruv"),
    path("statistika/", views.statistika, name="statistika"),
    path("aloqa/", views.aloqa, name="aloqa"),
    path("collocation/", views.collocation, name="collocation"),
    path("ngram/", views.ngram, name="ngram"),
    path("kwic/", views.kwic, name="kwic"),
]
