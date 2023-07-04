
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

admin.site.register(User)
admin.site.register(Class)
admin.site.register(Teacher)
admin.site.register(Student)
admin.site.register(Lectures)
admin.site.register(Assignment)
admin.site.register(AssignmentAssigned)
admin.site.register(Colors)
admin.site.register(OTP)