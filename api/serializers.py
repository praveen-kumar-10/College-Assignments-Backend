from django.db import models
from rest_framework.serializers import ModelSerializer
from .models import User, Teacher


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = '_all_'


class TeacherSerializer(ModelSerializer):
    class Meta:
        model = Teacher
        fields = ['id', 'name', 'gender', 'phone', 'department', 'mail', 'user_type']
