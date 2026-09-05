from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from . import views


class GETLogoutView(auth_views.LogoutView):
    """Allow GET-based logout for simple navbar link clicks."""
    http_method_names = ['get', 'post', 'options']

    def get(self, request, *args, **kwargs):
        auth_logout(request)
        return redirect(self.next_page or 'accounts:login')


app_name = 'accounts'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', GETLogoutView.as_view(template_name='registration/logged_out.html'), name='logout'),
    path('redirect/', views.role_redirect, name='role_redirect'),
    path('profile/', views.profile_view, name='profile'),
    path('users/', views.user_list, name='user_list'),
]
