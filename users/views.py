from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from .models import *
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import auth
from django.db import transaction
from django.contrib.auth.hashers import check_password
from synergy.utils import *
from synergy.celery import send_email
from rest_framework_simplejwt.tokens import UntypedToken

from django.utils import timezone

from api.utils import *
from datetime import datetime as dt
import time
from synergy.celery import send_email
import math
import random


# Create your views here.

@csrf_exempt
@api_view(['POST'])
def register(request):
    try:
        email = request.data["email"].lower()
        password = request.data["password"]
        name = request.data['name']
        gender = request.data["gender"]
        phone = request.data['phone']
        department = request.data['department']
        profession = request.data['profession']
    except KeyError as e:
        e = str(e)
        return Response({"success": "0", "message": f"Please provide {e}"}, status=400)
    except Exception as e:
        return Response({"success": "0", "message": "Something went wrong"}, status=400)
    try:
        with transaction.atomic():
            if User.objects.filter(email=email):
                return Response({"success": "0", "message": "Email already exists"}, status=200)
            else:
                user = User.objects.create_user(
                    username=email, email=email, password=password, user_type="teacher")
                Teacher.objects.create(
                    user=user, name=name, gender=gender, phone=phone, department=department, profession=profession)
                return Response({"success": "1", "message": "User registered successfully", "user": {"email": email, "gender": gender, "user_type": "teacher", "name": name, "department": department, "phone": phone}}, status=200)
    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"}, status=400)


@csrf_exempt
@api_view(['POST'])
def login(request):
    try:
        email = request.data["email"].lower()
        password = request.data["password"]
    except KeyError as e:
        e = str(e)
        return Response({"success": "0", "message": f"Please provide {e}"}, status=400)
    except Exception as e:
        return Response({"success": "0", "message": "Something went wrong"}, status=400)
    try:
        user = User.objects.filter(email=email).first()
        if user is None:
            return Response({"success": "0", "message": "Email doesnot exists"}, status=200)
        if not check_password(password, user.password):
            return Response({"success": "0", "message": "Incorrect Password"}, status=200)
        if not user.verified:
            return Response({"success": "2", "message": "Consult your admin to activate your account"}, status=200)
        refresh = RefreshToken.for_user(user)

        refresh['user_id'] = user.id
        print('hi')
        name = ''
        if user.user_type == 'teacher':
            z = Teacher.objects.filter(user=user).first()
            name = z.name
        elif user.user_type == 'student':
            z = Student.objects.filter(user=user).first()
            name = z.name
        else:
            z = user

        return Response({
            "success": "1",
            "message": "logged in successfully",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                        "email": user.email,
                        "user_type": user.user_type,
                        "id": z.id,
                        "name": name
                        }
        }, status=200)
    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"}, status=400)


@csrf_exempt
@api_view(["POST"])
# @ValidateAuthenticationToken
def logout(request, user=None):
    return Response({"success": "1", "message": "Logged out successfully"})


@csrf_exempt
@api_view(["GET"])
@ValidateAuthenticationToken
def Test(request, user=None):
    return Response({"success": "1", "message": user.id})


@csrf_exempt
@api_view(["GET"])
def send_email_view(request):

    # context = {
    # 	"title":"Title",
    #     "subject":"Subj1",
    #     # "deadLine":dt.now(),
    #     # "assignmentLink":'https://firebasestorage.googleapis.com/v0/b/clg-proj-5d15e.appspot.com/o/assignments%2Ftitle31667706274364792013?alt=media&token=2'
    # }

    context = {
        "title": 'Title',
        "subject": 'Subject',
        "due_date": dt.now(),
        "semester": 2,
        "assignmentLink": 'https://firebasestorage.googleapis.com/v0/b/clg-proj-5d15e.appspot.com/o/assignments_answers%2F2019%2FCSE%2FC%2FSubj1%2FJavaScript%20Interview%20Guide%20-%20Preview%20(2).pdf1676809712753511841?alt=media&token=149db2a1-905c-4b65-8344-b4d25b3dd997'
    }
    html, text = get_email_description(context, 'dueAssignment')

    india = pytz.timezone('Asia/Kolkata')
    time = dt.now()
    time = time.astimezone(india)
    time = time + timedelta(minutes=1)
    send_email.apply_async(
        ("Remainer to complete your work", text, html, "praveennetinti2002@gmail.com"), eta=time)

    # send_email.delay()
    # html,text = get_email_description(context,'gradedAssignment')

    # send_email.delay("Congrats, Your assignment was awarded",text,html,"19bq1a05e7@vvit.net")

    return Response({"messagee": "email send"})


@csrf_exempt
@ValidateAuthenticationToken
@api_view(["GET"])
def getAdminProfile(request, user=None):
    if user == None:
        return Response({"success": "0", "message": "Something went wrong"}, status=400)
    try:
        admin_id = request.GET.get('admin_id')
        admin = User.objects.filter(id=admin_id).first()
        data = {}

        data['email'] = admin.email
        data['user_type'] = admin.user_type
        data['first_name'] = admin.first_name
        data['last_name'] = admin.last_name

        return Response({
            "success": "1",
            "data": data
        }, status=200)

    except Exception as e:
        print('ERROR', e)
        return Response({
            "success": "0",
            "message": "Something went wrong."
        })


@csrf_exempt
@ValidateAuthenticationToken
@api_view(["GET"])
def getTeacherProfile(request, user=None):
    if user == None:
        return Response({"success": "0", "message": "Something went wrong"}, status=400)
    try:

        email = request.GET.get('email')
        user = User.objects.filter(email=email).first()

        if user is None:
            return Response({"success": "0", "message": "Email doesnot exists"}, status=200)

        teacher = Teacher.objects.filter(user=user).first()
        data = {
            "id": teacher.id,
            "name": teacher.name,
            "email": user.email,
            "user_type": user.user_type,
            "gender": teacher.gender,
            "phone": teacher.phone,
            "department": teacher.department
        }

        return Response({
            "success": "1",
            "data": data
        }, status=200)

    except Exception as e:
        print('ERROR', e)
        return Response({
            "success": "0",
            "message": "Something went wrong."
        })


@csrf_exempt
@ValidateAuthenticationToken
@api_view(["GET"])
def getStudentProfile(request, user=None):
    print(226)
    if user == None:
        return Response({"success": "0", "message": "Something went wrong"}, status=400)
    else:
        try:
            email = request.GET.get('email')
            user = User.objects.filter(email=email).first()

            if user is None:
                return Response({"success": "0", "message": "Email doesnot exists"}, status=200)

            student = Student.objects.filter(user=user).first()
            data = {
                "id": student.id,
                "name": student.name,
                "email": user.email,
                "user_type": user.user_type,
                "gender": student.gender,
                "phone": student.phone,
                "roll_no": student.roll_no,
                'joinedIn': student.class_obj.year,
                'currentYear': student.class_obj.edu_year,
                'currentBranch': student.class_obj.branch,
                'currentSection': student.class_obj.section,
                'currentSemester': student.class_obj.semester
            }

            return Response({
                "success": "1",
                "data": data
            }, status=200)

        except Exception as e:
            print('ERROR', e)
            return Response({
                "success": "0",
                "message": "Something went wrong."
            })


@csrf_exempt
@ValidateAuthenticationToken
@api_view(["GET"])
def get_student_profile(request, user=None):
    if user == None:
        return Response({"success": "0", "message": "Something went wrong"}, status=400)

    try:
        student_id = request.GET.get('studentId')
        student = Student.objects.filter(id=student_id).first()
        if user is None:
            return Response({"success": "0", "message": "Student doesnot exists"}, status=401)

        data = {}

        data['name'] = student.name
        data['joinedIn'] = student.class_obj.year
        data['currentYear'] = student.class_obj.edu_year
        data['roll_no'] = student.roll_no
        data['currentBranch'] = student.class_obj.branch
        data['currentSection'] = student.class_obj.section
        data['currentSemester'] = student.class_obj.semester
        data['phone_no'] = student.phone
        data['gender'] = student.gender
        return Response({
            "success": "1",
            "data": data,
        }, status=200)
    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"}, status=400)


@csrf_exempt
@api_view(["POST"])
def forgot_password(request):
    try:
        email = request.data['email']
        user = User.objects.filter(email=email).first()
        print('USER', user)
        if user == None:
            return Response({
                "success": "2",
                "message": "No user found with the email."
            }, status=200)

        otp = OTPgenerator()
        print("OTP", otp)
        otpUser = OTP.objects.filter(user=user).first()

        if otpUser == None:
            otpUser = OTP(user=user, otp=otp, generatedAt=dt.now(timezone.utc))
        else:
            otpUser.otp = otp
            otpUser.generatedAt = dt.now(timezone.utc)

        otpUser.save()
        context = {
            "otp": otp
        }
        html, text = get_email_description(context, 'otp')
        send_email.delay("Reset Password", text, html, email)

        return Response({
            "success": "1",
            "message": "OTP sent to your email successfully."
        }, status=200)

    except Exception as e:
        return Response({
            "success": "0",
            "message": "Something went wrong."
        }, status=400)


@csrf_exempt
@api_view(["POST"])
def change_password(request):
    try:
        email = request.data['email']
        otp = request.data['otp']
        password = request.data['password']

        user = User.objects.filter(email=email).first()

        if user == None:
            return Response({
                "success": "0",
                "message": "No user found with the email."
            }, status=400)

        otpObject = OTP.objects.filter(user=user).first()

        if otpObject == None:
            return Response({
                "success": "0",
                "message": "Something went wrong."
            }, status=400)

        current_date = dt.now(timezone.utc)
        diff = current_date - otpObject.generatedAt

        if diff.seconds > (10*60):
            return Response({
                "success": "0",
                "message": "OTP expired."
            }, status=410)

        if otp != otpObject.otp:
            return Response({
                "success": "0",
                "message": "OTP not same"
            }, status=400)

        user.set_password(password)
        user.save()
        return Response({
            "success": "1",
            "message": "Password changed successfully."
        }, status=200)
    except KeyError as e:
        e = str(e)
        return Response({"success": "0", "message": f"Please provide {e}"}, status=200)
    except Exception as e:
        print(e)
        return Response({
            "success": "0",
            "message": "Something went wrong"
        }, status=400)


def OTPgenerator():
    digits = "0123456789"
    OTP = ""

    for i in range(6):
        OTP += digits[math.floor(random.random() * 10)]

    return OTP


# promotion

# 4
# 3
# 2
# 1

# year = 4
# students=Student.objects.filter(class_obj__year=year)

# for student in students
# 	prev_class = stundet.class_obj# 4,1
# 	student.class_obj = Class(year,)

# Student.filter()
