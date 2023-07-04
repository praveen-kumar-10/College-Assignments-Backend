from email.policy import default
import random
from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import datetime as dt

# Create your models here.


class User(AbstractUser):
    email = models.TextField(default=None, null=True, unique=True)
    # password = models.TextField(default=None, null=True)
    # student, teacher, local_admin, super_admin
    user_type = models.TextField(default=None, null=True)
    verified = models.BooleanField(default=False, null=True)
    is_active = models.BooleanField(default=False, null=True)

    def _str_(self):
        return self.email


class Class(models.Model):
    year = models.TextField(default=None, null=True)  # 2019 etc
    edu_year = models.TextField(default=None, null=True)  # 1st, 2nd etc
    branch = models.TextField(default=None, null=True)
    section = models.TextField(default=None, null=True)
    semester = models.TextField(default=None, null=True)
    # user_id = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.year) + '-' + str(self.edu_year) + "-" + str(self.branch) + "-" + str(self.section) + '-' + str(self.semester)


class Teacher(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=None, null=True)
    name = models.TextField(default=None, null=False)
    gender = models.TextField(default=None, null=True)
    phone = models.CharField(null=False, max_length=10, unique=True)
    department = models.TextField(default=None, null=False)
    profession = models.TextField(default='Assistant Professor',blank=True,null=True)

    def __str__(self):
        return self.name


class Student(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, default=None, null=True)
    roll_no = models.CharField(null=False, max_length=10, unique=True)
    gender = models.TextField(default=None, null=True)
    phone = models.CharField(null=True, max_length=10,
                             unique=True, default=None)
    name = models.TextField(default=None, null=False)
    class_obj = models.ForeignKey(
        Class, on_delete=models.CASCADE, default=None, null=True)

    def __str__(self):
        return self.roll_no


class Lectures(models.Model):
    class_obj = models.ForeignKey(
        Class, on_delete=models.CASCADE, default=None, null=True)
    teacher = models.ForeignKey(
        Teacher, on_delete=models.CASCADE, default=None, null=True)
    subject = models.TextField(default=None, null=True)
    subject_code = models.TextField(default=None, null=True)


# class StudentClassMapping(models.Model):
# 	class_obj = models.ForeignKey(Class)
# 	student = models.ForeignKey(Student)


class Assignment(models.Model):
    title = models.TextField(default=None, null=True)
    due_date = models.DateTimeField(default=None, blank=False)
    date = models.DateTimeField(default=None, blank=False)
    assignment_link = models.TextField(default=None, null=True)
    assigned_by = models.ForeignKey(
        Teacher, on_delete=models.CASCADE, default=None, null=True)
    subject = models.TextField(default=None, null=True)
    subject_code = models.TextField(default=None, null=True)
    semester = models.IntegerField(default=None, null=False)
    class_obj = models.ForeignKey(
        Class, on_delete=models.CASCADE, default=None)

    def __str__(self):
        return str(self.class_obj)+"/"+self.title


class AssignmentAssigned(models.Model):
    assignment = models.ForeignKey(
        Assignment, on_delete=models.CASCADE, default=None, null=True)
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, default=None, null=True)
    class_obj = models.ForeignKey(
        Class, on_delete=models.CASCADE, default=None)
    answer_link = models.TextField(default=None, null=True)
    date_submitted = models.DateTimeField(default=None, null=True)
    is_submitted = models.BooleanField(default=False, null=True)
    marks = models.IntegerField(default=None, null=True)
    feedback = models.TextField(default=None, null=True)
    semester = models.IntegerField(default=None, null=False)

    def __str__(self):
        return str(self.class_obj)+'/'+self.assignment.subject+'/'+self.student.roll_no


class Colors(models.Model):
    subject = models.TextField(default=None, null=True)
    color = models.TextField(default=None, null=True)

    def save(self, *args, **kwargs):
        colors = [
            '#000000',
            '#36454F',
            '#023020',
            '#FF5733',
            '#008000',
            '#808080',
            '#FF0000',
            '#0000FF'
        ]
        color = random.choice(colors)
        self.color = color
        super().save(*args, **kwargs)


class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.TextField(default=None, null=False)
    generatedAt = models.DateTimeField(default=dt.now)

# /api/forget_password

# body = email

# userid

# generate otp

# OTP.save() with time and send a mail with to the user.

# /api/reset_password

# email and otp and password

# checking

# dt.now() - generatedAt < 5min

# updated

# react
