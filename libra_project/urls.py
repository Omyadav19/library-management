from django.contrib import admin
from django.urls import path
from library import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard, name='dashboard'),
    path('books/', views.books_view, name='books'),
    path('add_book/', views.add_book, name='add_book'),
    path('search/', views.search, name='search'),
    path('issue_book/', views.issue_book, name='issue_book'),
    path('return_book/', views.return_book, name='return_book'),
    path('issued/', views.issued, name='issued'),
    path('overdue/', views.overdue, name='overdue'),
    path('member_history/', views.member_history, name='member_history'),
    path('delete_book/<str:book_id>/', views.delete_book, name='delete_book'),
    path('renew/<str:issue_id>/', views.renew, name='renew'),
    path('report/', views.report, name='report'),
    path('settings/', views.settings, name='settings'),
    
    # APIs
    path('api/validate_isbn/', views.api_validate_isbn, name='api_validate_isbn'),
    path('api/activity/', views.api_activity, name='api_activity'),
    path('api/book/<str:book_id>/', views.api_book, name='api_book'),
]
