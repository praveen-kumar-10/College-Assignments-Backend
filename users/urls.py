from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.views import TokenBlacklistView
from .views import *

urlpatterns = [
    path('login', login),
    path('o/token', TokenRefreshView.as_view()),
    path('signup', register),
    path('logout', TokenBlacklistView.as_view()),
    path('profile', get_student_profile),
    path('admin-profile', getAdminProfile),
    path('teacher-profile', getTeacherProfile),
    path('student-profile', getStudentProfile),
    path('test', Test),
    path('send_email', send_email_view),
    path('reset-password', forgot_password),
    path('change-password', change_password)
]
