import dateutil.parser as dt
import json
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from .models import *
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import auth
from django.db import transaction
from django.contrib.auth.hashers import check_password
from synergy.utils import *
from .exceptions import *
import pyrebase
from synergy.settings import *
from tablib import Dataset

from synergy.celery import send_email
from .utils import *
from datetime import datetime as dtime
import time

import xlsxwriter

from django.http import *
# Create your views here.


@csrf_exempt
@api_view(["GET"])
@ValidateAuthenticationToken
def get_teachers(request, user=None):
    # print(user)
    if user.user_type != "admin":
        return Response({"success": "3", "message": "Not Authorized"}, status=401)
    try:
        data = Teacher.objects.all()
        teachers = []
        for i in data:
            teacher = {}
            teacher['id'] = i.id
            teacher['name'] = i.name
            teacher['gender'] = i.gender
            teacher['phone'] = i.phone
            teacher['department'] = i.department
            teacher['mail'] = i.user.email
            teacher['user_type'] = i.user.user_type
            teacher['approved'] = i.user.verified
            teacher['job_title'] = 'assistant professor'

            teachers.append(teacher)
    except Exception as e:
        return Response({"success": "0", "message": "Something went wrong."}, status=403)

    return Response({"success": "1", "teachers": teachers}, status=200)


@csrf_exempt
@api_view(["POST"])
@ValidateAuthenticationToken
def handle_approve(request, user=None):
    if user.user_type != "admin":
        return Response({"success": "3", "message": "Not Authorized"}, status=401)
    try:
        teacher_id = request.data['id']
        approve = request.data['approve']
    except KeyError as e:
        e = str(e)
        return Response({"success": "0", "message": f"Please provide {e}"}, status=400)
    try:
        teacher = Teacher.objects.filter(id=teacher_id).first()
        user = User.objects.filter(id=teacher.user.id).first()
        user.verified = approve
        user.save()
        # send__r
        if approve:
            return Response({"success": "1", "message": "Teacher Approved Successfully"}, status=200)
        else:
            return Response({"success": "1", "message": "Teacher Disapproved Successfully"})
    except Exception as e:
        return Response({"success": "0", "message": "Something went wrong."}, status=400)


@api_view(['GET'])
@csrf_exempt
@ValidateAuthenticationToken
def check_admin(request, user=None):
    if user.user_type != "admin":
        return Response({"success": "3", "message": "Not Authorized"}, status=401)
    else:
        return Response({"success": "1", "message": "Is Admin"}, status=200)


# student:- roll, name, year, branch, section, batch

# subjects:- teacher_name, year, branch, section, subject, email , phone


# 1. year, branch, section, batch, semister -> promote


# {
# 	"classes": [
# 		{
# 			"year": 1,
# 			"branch": "mech",
# 			"section": "a"
# 		},
# 		{
# 			"year": 1,
# 			"branch": "eee",
# 			"section": "a"
# 		}
# 	]
# }


@api_view(['POST'])
@csrf_exempt
@ValidateAuthenticationToken
def createBulkStudents(request, user=None):
    if user.user_type != "admin":
        return Response({"success": "3", "message": "Not Authorized"}, status=401)
    try:
        file = request.FILES["file"]
    except KeyError as e:
        e = str(e)
        return Response({"success": "0", "message": f"Please provide {e}"}, status=400)
    except Exception as e:
        return Response({"success": "0", "message": "Something went wrong"}, status=400)
    try:
        with transaction.atomic():
            dataset = Dataset()
            imported_data = dataset.load(file.read())
            headings = {"name", "regno", "year", "branch",
                        "section", "batch", "semester", "phone"}
            heading_index_mapping = {}
            for idx, heading in enumerate(imported_data.headers):
                if heading.lower() not in headings:
                    raise RollBackTransaction(
                        {"success": "0", "message": f"unknown heading {heading} in the file"})
                heading_index_mapping[heading.lower()] = idx
            for heading in headings:
                if heading not in heading_index_mapping:
                    raise RollBackTransaction(
                        {"success": "0", "message": f"cannot find heading {heading} in the file"})
            for data in imported_data:
                if data[heading_index_mapping["regno"]] == None:
                    continue
                email = data[heading_index_mapping["regno"]].lower() + \
                    "@vvit.net"
                if User.objects.filter(email=email):
                    raise RollBackTransaction(
                        {"success": "0", "message": f"Regno {data[heading_index_mapping['regno']]} already exists"}, status=400)
                else:
                    password = data[heading_index_mapping["regno"]].lower()
                    regno = password
                    name = data[heading_index_mapping["name"]]
                    phone = data[heading_index_mapping["phone"]]
                    year = data[heading_index_mapping["year"]]  # 4,3,2,1
                    branch = data[heading_index_mapping["branch"]]
                    semester = data[heading_index_mapping["semester"]]
                    phone = data[heading_index_mapping["phone"]]
                    section = data[heading_index_mapping["section"]]
                    batch = data[heading_index_mapping["batch"]]  # 2019
                    user = User.objects.create_user(
                        username=email, email=email, password=password, user_type="student", verified=True)
                    class_obj = Class.objects.filter(
                        year=batch, branch=branch, semester=semester, section=section, edu_year=year)
                    # print(class_obj)
                    if len(class_obj) == 0:
                        class_obj = [Class.objects.create(
                            year=batch, branch=branch, semester=semester, section=section, edu_year=year)]
                    Student.objects.create(
                        user=user, name=name, phone=phone, roll_no=regno, class_obj=class_obj[0])
    except RollBackTransaction as e:
        print(e)
        e = eval(json.loads(json.dumps(str(e))))
        return Response(e)
    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong!!"}, status=400)
    return Response({"success": "1", "message": "Students Created Successfully"})


@csrf_exempt
@ValidateAuthenticationToken
@api_view(["POST"])
def promote_student(request, user=None):
    if user.user_type != "admin":
        return Response({"success": "3", "message": "Not Authorized"}, status=401)

    try:
        with transaction.atomic():
            year = request.data['year']
            edu_year = request.data['edu_year']
            students = Student.objects.filter(
                class_obj__year=year, class_obj__edu_year=edu_year)

            for student in students:
                student_class = student.class_obj
                semester = student_class.semester

                if int(semester) == 1:
                    semester = 2
                else:
                    edu_year = int(edu_year) + 1
                    semester = 1
                print(year, edu_year, semester)
                new_class = Class.objects.filter(
                    year=year, edu_year=edu_year, branch=student_class.branch, section=student_class.section, semester=semester).first()
                if new_class == None:
                    new_class = Class(year=year, edu_year=edu_year, branch=student_class.branch,
                                      section=student_class.section, semester=semester)
                    new_class.save()
                student.class_obj = new_class
                print(new_class)
                student.save()
    except RollBackTransaction as e:
        print(e)
        e = eval(json.loads(json.dumps(str(e))))
        return Response(e)
    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong!!"}, status=400)
    return Response({"success": "1", "message": "Students Promoted Successfully"})


@csrf_exempt
@ValidateAuthenticationToken
@api_view(["POST"])
def promote_student_confirm(request, user=None):
    if user.user_type != "admin":
        return Response({"success": "3", "message": "Not Authorized"}, status=401)
    try:
        with transaction.atomic():
            year = request.data['year']
            edu_year = request.data['edu_year']

            classs = Class.objects.filter(
                edu_year=edu_year, year=year, semester='2').first()
            if classs == None:
                classs = Class.objects.filter(
                    edu_year=edu_year, year=year, semester='1').first()
                if classs == None:
                    return Response({"success": "0", "message": "Cannot promote!!"}, status=400)

                return Response({"success": "1", "message": "Students are in semester 1, Promote?"}, status=200)
            return Response({"success": "1", "message": "Students are in semester 2, Promote?"}, status=200)

    except RollBackTransaction as e:
        print(e)
        e = eval(json.loads(json.dumps(str(e))))
        return Response(e)
    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong!!"}, status=400)


@api_view(['POST'])
@csrf_exempt
@ValidateAuthenticationToken
def createBulkSubjects(request, user=None):
    if user.user_type != "admin":
        return Response({"success": "3", "message": "Not Authorized"}, status=401)

    try:
        file = request.FILES["file"]
    except KeyError as e:
        e = str(e)
        return Response({"success": "0", "message": f"Please provide {e}"}, status=400)
    except Exception as e:
        return Response({"success": "0", "message": "Something went wrong"}, status=400)
    try:
        with transaction.atomic():
            dataset = Dataset()
            imported_data = dataset.load(file.read(), format='xlsx')
            headings = {"teacher_email", "year", "branch", "section",
                        "semester", "subject", "subject_code", "batch"}
            heading_index_mapping = {}
            for idx, heading in enumerate(imported_data.headers):
                if heading.lower() not in headings:
                    raise RollBackTransaction(
                        {"success": "0", "message": f"unknown heading {heading} in the file"})
                heading_index_mapping[heading.lower()] = idx
            # print(heading_index_mapping)
            for heading in headings:
                if heading not in heading_index_mapping:
                    raise RollBackTransaction(
                        {"success": "0", "message": f"cannot find heading {heading} in the file"})
            for data in imported_data:
                # email = data[heading_index_mapping["regno"]].lower() + "@vvit.net"
                email = data[heading_index_mapping["teacher_email"]]
                year = data[heading_index_mapping["year"]]
                branch = data[heading_index_mapping["branch"]]
                semester = data[heading_index_mapping["semester"]]
                section = data[heading_index_mapping["section"]]
                subject = data[heading_index_mapping["subject"]]
                batch = data[heading_index_mapping["batch"]]
                subject_code = data[heading_index_mapping['subject_code']]
                print('a')
                if subject_code == None or subject == None:
                    continue
                print('b')
                teacher = Teacher.objects.filter(user__email=email).first()
                class_obj = Class.objects.filter(
                    year=batch, branch=branch, semester=semester, section=section, edu_year=year).first()

                if class_obj == None:
                    class_obj = Class.objects.create(
                        edu_year=year, branch=branch, semester=semester, section=section, year=batch)
                Lectures.objects.create(
                    teacher=teacher, class_obj=class_obj, subject=subject, subject_code=subject_code)
                Colors.objects.create(subject=subject)
    except RollBackTransaction as e:
        e = eval(json.loads(json.dumps(str(e))))
        return Response(e)
    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"})
    return Response({"success": "1", "message": "Subjects Created Successfully"})

# @api_view(['POST'])
# @ValidateAuthenticationToken
# @csrf_exempt
# def createClass(request, user=None):
# 	# if user.user_type != "admin":
# 	# 	return Response({"success": "3", "message": "Not Authorized"}, status=401)
# 	try:
# 		year = request.data["year"]
# 		edu_year = request.data["edu_year"]
# 		branch = request.data["branch"]
# 		section = request.data["section"]
# 		semester = request.data["semester"]
# 	except KeyError as e:
# 		e = str(e)
# 		return Response({"success": "0", "message": f"Please provide {e}"}, status=400)
# 	except Exception as e:
# 		return Response({"success": "0", "message": "Something went wrong"}, status=400)
# 	try:
# 		with transaction.atomic():
# 			class_obj = Class.objects.create(year=year, edu_year=edu_year, branch=branch, section=section, semester=semester)
# 			return Response({"success": "1", "message": "Class created successfully", "class": {"id": class_obj.id}})
# 	except Exception as e:
# 		print(e)
# 		return Response({"success": "0", "message": "Something went wrong"}, status=400)


@api_view(['POST'])
@ValidateAuthenticationToken
@csrf_exempt
def create_assignment(request, user=None):

    if user.user_type != 'teacher':
        return Response({"success": "3", "message": "Not Authorized"}, status=401)

    try:
        title = request.data['title']
        due_date = dt.parse(request.data['due_date']).replace(
            hour=0, minute=0, second=0)
        date = dt.parse(request.data['date']).replace(
            hour=0, minute=0, second=0)
        file = request.FILES['file']
        year = int(request.data['year'])  # 2019
        edu_year = int(request.data['edu_year'])  # 1,2,3,4
        branch = request.data['branch']
        section = request.data['section']
        subject = request.data['subject']
        semester = int(request.data['semester'])
        # subject_code = request.data['subject_code']

    except KeyError as e:
        e = str(e)
        return Response({"success": "0", "message": f"Please provide {e}"}, status=400)
    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"}, status=400)

    try:
        if due_date < date:
            return Response({"success": "0", "message": "Due cannot be past"}, status=400)

        # return Response({"success": "0", "message": "Something went wrong"}, status=400)
        print('hi')
        with transaction.atomic():
            config = {
                "apiKey": apiKey,
                "authDomain": authDomain,
                "databaseURL": databaseURL,
                "storageBucket": storageBucket
            }
            firebase = pyrebase.initialize_app(config)
            storage = firebase.storage()
            filename = 'assignments_questions/'+str(year)+'/'+str(branch)+'/'+str(
                section)+'/' + str(subject) + '/' + title+''+str(time.time_ns())
            t = str(user.id)
            # print(filename)
            s = storage.child(filename).put(file, t)
            # print(s)
            print('hi')
            link = storage.child(filename).get_url(t)
            print(link)
            teacher = Teacher.objects.filter(user=user)[0]
            print(teacher)

            lectures = Lectures.objects.filter(subject=subject).first()
            print(lectures)
            if lectures == None:
                return Response({
                    "success": "0",
                    "message": "Invalid assignment post."
                }, 401)
            subject_code = lectures.subject_code

            clas = Class.objects.filter(
                year=year, edu_year=edu_year, branch=branch, section=section, semester=semester)[0]
            print(clas)

            assignment = Assignment(title=title, due_date=due_date, date=date, assignment_link=link,
                                    assigned_by=teacher, subject=subject, subject_code=subject_code, semester=semester, class_obj=clas)
            assignment.save()

            print(year, branch, section)
            # Class.objects.filter(year=4,branch='CSE',section='C'
            # for section in sections:

            students = Student.objects.filter(class_obj=clas)

            context = {
                "topic": title,
                "subject": subject,
                "semester": semester,
                "deadLine": due_date,
                "assignmentLink": link
            }

            htmlN, textN = get_email_description(context, 'newAssignment')
            htmlD, textN = get_email_description(context, 'dueAssignment')
            days = get_days_before_due_date(date, due_date)
            timeForMail = date + timedelta(days=days)
            print('sucessfully saved')
            # return Response({"success": "0", "message": "Something went wrong"}, status=400)

            for student in students:
                assignmentAssigned = AssignmentAssigned(
                    assignment=assignment, student=student, semester=semester, class_obj=clas)
                assignmentAssigned.save()
                # send_email.delay("Complete Your Assignment Before Deadline ",textN,htmlN,student.user.email)
                # send_email.apply_async(("Complete Your Assignment Before Deadline ",textN,htmlN,student.user.email), eta=timeForMail)

            send_email.delay("Complete Your Assignment Before Deadline ",
                             textN, htmlN, '19bq1a05f1@vvit.net')
            return Response({
                "success": "1", "assignmentLink": link,
            }, 200)

    except Exception as e:
        print(e, 'asdasd')
        return Response({"success": "0", "message": "Something went wrong"}, status=400)


@api_view(["GET"])
@csrf_exempt
@ValidateAuthenticationToken
def get_assignment_students(request, user=None):

    if user == None:
        return Response({"success": "0", "message": "You are not allowed to access this resource please authenticate"}, status=401)

    # print(user)

    try:
        student = Student.objects.filter(user=user).first()
        current_edu_year = student.class_obj.edu_year
        # print(student)
        if student == None:
            return Response({"success": "0", "message": "Something went wrong"}, status=400)
        assignmentAssigneds = AssignmentAssigned.objects.filter(
            student=student, semester=student.class_obj.semester, student__class_obj__edu_year=current_edu_year)
        assignments = []
        print('hi')
        for assignmentAssigned in assignmentAssigneds:
            assignment = assignmentAssigned.assignment
            # print(student.name)
            # print(student.class_obj.edu_year+student.class_obj.branch+student.class_obj.section)
            # print(assignment.assigned_by.name)
            # print(assignment.subject)

            subject = assignment.subject
            # print(subject,assignment.subject_code,"dsfjsdkfks")
            color = Colors.objects.filter(subject=subject).first()
            assignments.append({
                "id": assignmentAssigned.id,
                "title": assignment.title,
                "assignment_link": assignment.assignment_link,
                "datePosted": assignment.date,
                "due_date": assignment.due_date,
                "assignedBy": {
                    "teacherId": assignment.assigned_by.id,
                    "teacherName": assignment.assigned_by.name,
                },
                "marks": assignmentAssigned.marks,
                "feedback": assignmentAssigned.feedback,
                "reviewed": (assignmentAssigned.marks != None and True) or False,
                "submitted": assignmentAssigned.is_submitted,
                "answerlink": assignmentAssigned.answer_link,
                "subject_full_code": subject,
                "subject_short_code": assignment.subject_code,
                "color_code": color.color,
                "submission_date": assignmentAssigned.date_submitted,
                "semester": student.class_obj.semester
            })

        return Response({
            "success": "0",
            "data": assignments
        }, 200)

    except Exception as e:
        print(e, 'a')
        return Response({"success": "0", "message": "Something went wrong"}, status=400)


@api_view(["GET"])
@csrf_exempt
@ValidateAuthenticationToken
def get_student_assignment_id(request, id, user=None):
    if user == None:
        return Response({"success": "0", "message": "You are not allowed to access this resource please authenticate"}, status=401)

    try:
        assignmentAssigned = AssignmentAssigned.objects.filter(id=id).first()
        if assignmentAssigned == None:
            return Response({"success": "0", "message": "There is no assignment for this id"}, status=404)

        assignment = assignmentAssigned.assignment

        subject = assignment.subject
        # print(subject,assignment.subject_code,"dsfjsdkfks")
        color = Colors.objects.filter(subject=subject).first()
        data = {
            "id": assignmentAssigned.id,
            "title": assignment.title,
            "assignment_link": assignment.assignment_link,
            "datePosted": assignment.date,
            "due_date": assignment.due_date,
            "assignedBy": {
                "teacherId": assignment.assigned_by.id,
                "teacherName": assignment.assigned_by.name,
            },
            "marks": assignmentAssigned.marks,
            "feedback": assignmentAssigned.feedback,
            "reviewed": (assignmentAssigned.marks != None and True) or False,
            "submitted": assignmentAssigned.is_submitted,
            "answerlink": assignmentAssigned.answer_link,
            "subject_full_code": subject,
            "subject_short_code": assignment.subject_code,
            "color_code": color.color,
            "submission_date": assignmentAssigned.date_submitted
        }

        return Response({
            "success": "0",
            "data": data
        }, 200)
    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"}, status=400)


@api_view(['POST'])
@ValidateAuthenticationToken
@csrf_exempt
def submit_assignment(request, user=None):
    if user.user_type != 'student':
        return Response({"success": "3", "message": "Not Authorized"}, status=401)

    try:
        file = request.FILES['file']
        assignmentId = request.data['assignmentId']
        date = dt.parse(request.data['date_submitted']).replace(
            hour=0, minute=0, second=0)
        print(assignmentId)
    except KeyError as e:
        e = str(e)
        print(e)
        return Response({"success": "0", "message": f"Please provide {e}"}, status=400)
    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"}, status=400)
    try:
        with transaction.atomic():
            student = Student.objects.filter(user=user)[0]
            print(student)
            z = AssignmentAssigned.objects.filter(
                student=student, id=assignmentId)
            assignmentAssigned = z[0]
            assignment = assignmentAssigned.assignment
            # print(assignmentId,assignment)
            # return Response({"success": "0", "message": "Something went wrong"}, status=400)

            clas = student.class_obj

            if len(z) == 0:
                return Response({"success": "1", "message": "Assignment not found"}, 404)

            config = {
                "apiKey": apiKey,
                "authDomain": authDomain,
                "databaseURL": databaseURL,
                "storageBucket": storageBucket
            }

            firebase = pyrebase.initialize_app(config)
            storage = firebase.storage()
            # filename = 'assignments_questions/'+str(year)+'/'+str(branch)+'/'+str(section)+'/'+title+''+str(time.time_ns())

            filename = 'assignments_answers/'+str(clas.year)+'/'+str(clas.branch)+'/'+str(
                clas.section)+'/'+str(assignment.subject)+'/'+str(file)+''+str(time.time_ns())
            t = str(assignmentAssigned.id)
            print(t)
            s = storage.child(filename).put(file)
            link = storage.child(filename).get_url(s['downloadTokens'])
            print(link)
            student = Student.objects.filter(user=user)[0]

            assignmentAssigned.answer_link = link
            assignmentAssigned.is_submitted = True
            assignmentAssigned.date_submitted = date

            context = {
                "title": assignment.title,
                "subject": assignment.subject,
                "submissionTime": date,
                "submissionLink": link
            }

            html, text = get_email_description(context, 'submittedAssignment')

            send_email.delay("Successfull submitted", text, html, user.email)

            assignmentAssigned.save()
            return Response({
                "success": "1", "assignmentLink": link,
            }, 200)

    except Exception as e:
        print(e, 'asdasd')
        return Response({"success": "0", "message": "Something went wrong"}, status=400)


@api_view(['POST'])
@ValidateAuthenticationToken
@csrf_exempt
def assign_marks_feedback(request, user=None):
    if user.user_type != 'teacher':
        return Response({"success": "3", "message": "Not Authorized"}, status=401)

    try:
        with transaction.atomic():
            marks = request.data['marks']
            feedback = request.data['feedback']
            assignmentId = request.data['assignmentId']  # submission_id
            studentId = request.data['studentId']
            print(marks, feedback, assignmentId, studentId)

            student = Student.objects.filter(id=studentId)[0]
            print(student)
            assignmentAssigned = AssignmentAssigned.objects.filter(
                id=assignmentId, student=student)
            print(assignmentAssigned)
            if len(assignmentAssigned) == 0:
                return Response({"success": "0", "message": "Something went wrong"}, status=400)

            assignmentAssigned = assignmentAssigned[0]

            if assignmentAssigned.answer_link == None:
                return Response({
                    "success": "1",
                    "message": "The student didnt submitted the assignment."
                }, 401)
            assignmentAssigned.marks = marks
            assignmentAssigned.feedback = feedback
            assignmentAssigned.save()
            context = {
                "title": assignmentAssigned.assignment.title,
                "subject": assignmentAssigned.assignment.subject
            }
            html, text = get_email_description(context, 'gradedAssignment')
            send_email.delay("Congrats, Your assignment was awarded",
                             text, html, student.user.email)

    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"}, status=400)

    return Response({
        "success": "1",
        "message": "Marks assigned",
        "marks": marks,
        "feedback": feedback
    }, 200)


# @api_view(['GET'])
# # @ValidateAuthenticationToken
# @csrf_exempt
# def get_batches_branch_classes(request,user=None):
# 	# if user.user_type != 'teacher':
# 	# 	return Response({"success": "3", "message": "Not Authorized"}, status=401)

# 	try:
# 		classes = Class.objects.all()
# 		details = {}
# 		for classs in classes:
# 			year = classs.year
# 			edu_year = classs.edu_year
# 			branch = classs.branch
# 			section = classs.section
# 			# semester = classs.semester
# 			print(classs)
# 			# lectures = Lectures.objects.filter(class_obj = classs)
# 			# print(lectures)
# 			# if len(lectures) == 0:
# 			# 	continue
# 			# lectures = lectures[0]
# 			subject = lectures.subject

# 			if edu_year not in details:
# 				details[edu_year] = {
# 					"year":year,
# 					"branches":{}
# 				}

# 			if branch not in details[edu_year]['branches']:
# 				details[edu_year]['branches'][""+branch] = {
# 					"subject" : [],
# 					"sections" : []
# 				}
# 			details[edu_year]['branches'][""+branch]['subject'].append(subject)
# 			details[edu_year]['branches'][""+branch]['sections'].append(section)

# 		return Response({
# 			"success":"1",
# 			"details" : details
# 		})

# 	except Exception as e:
# 		print(e)
# 		return Response({"success": "0", "message": "Something went wrong"}, status=400)

@api_view(['GET'])
@ValidateAuthenticationToken
@csrf_exempt
def get_class_assignments_details(request, user=None):
    if user.user_type != 'teacher':
        return Response({
            "success": "3",
            "message": "Not authorized"
        }, status=401)
    try:
        year = request.GET.get('year')  # 4 CSE C 1 CC
        edu_year = request.GET.get('edu_year')
        branch = request.GET.get('branch')
        section = request.GET.get('section')
        subject = request.GET.get('subject')
        semester = request.GET.get('semester')
        # subject_code = request.GET.get('subject_code')

        class_obj = Class.objects.filter(
            year=year, edu_year=edu_year, branch=branch, section=section, semester=semester)
        print(class_obj)
        class_obj = class_obj.first()
        assignments = Assignment.objects.filter(class_obj=class_obj)

        if len(assignments) == None:
            return Response({
                "success": "0",
                "message": "No assignment for this subject."
            })

        data = {}
        for assignment in assignments:

            temp = {}
            temp['id'] = assignment.id
            temp['due_date'] = assignment.due_date
            temp['creation_date'] = assignment.date
            temp['subject'] = assignment.subject
            color = Colors.objects.filter(subject=assignment.subject).first()
            temp['subject_code'] = assignment.subject_code
            temp['subject_color'] = color.color
            temp['question_link'] = assignment.assignment_link
            temp['assignment_title'] = assignment.title

            data[assignment.title] = temp

        # if data == []:
        # 	return Response({
        # 		"success":"1",
        # 		"message":"NO assignments to show for this class."
        # 	},404)

        return Response({
            "success": "1",
            "data": data
        }, status=200)

    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"}, status=400)


@csrf_exempt
@ValidateAuthenticationToken
@api_view(["GET"])
def get_branches_by_year(request, user=None):  # 1,2,3,4

    if user.user_type != 'teacher':
        return Response({
            "success": "3",
            "message": "Not authorized"
        }, status=401)

    try:
        year = request.GET.get('year')
        edu_year = request.GET.get('edu_year')
        print(year, edu_year)
        branches_with_duplicates = [
            i.branch for i in Class.objects.filter(edu_year=edu_year, year=year)]
        branches_with_unique = list(set(branches_with_duplicates))

        if len(branches_with_unique) == 0:
            return Response({"success": "0", "message": "There are no branches for this year"}, status=200)

        return Response({
            "success": "1",
            "year": year,
            "data": branches_with_unique
        }, status=200)

    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"}, status=200)


@csrf_exempt
@ValidateAuthenticationToken
@api_view(["GET"])
def get_sections_by_branches_year(request, user=None):
    if user.user_type != 'teacher':
        return Response({
            "success": "3",
            "message": "Not authorized"
        }, status=401)

    try:
        year = request.GET.get('year')
        edu_year = request.GET.get('edu_year')
        branch = request.GET.get('branch')
        sections = list(set([i.section for i in Class.objects.filter(
            year=year, edu_year=edu_year, branch=branch)]))

        return Response({
            "success": "1",
            "year": year,
            "branch": branch,
            "data": sections
        }, status=200)

    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"}, status=400)


@csrf_exempt
@ValidateAuthenticationToken
@api_view(["GET"])
def get_subject_by_branch_year_section_sem(request, user=None):

    if user.user_type != 'teacher':
        return Response({
            "success": "3",
            "message": "Not authorized"
        }, status=401)

    try:
        edu_year = request.GET.get('edu_year')
        year = request.GET.get('year')
        branch = request.GET.get('branch')
        semester = request.GET.get('semester')
        section = request.GET.get('section')
        classs = Class.objects.filter(
            edu_year=edu_year, year=year, branch=branch, semester=semester, section=section).first()
        # print(classs)
        subjects = [{"subject": i.subject, "subject_code": i.subject_code}
                    for i in Lectures.objects.filter(class_obj=classs)]
        return Response({
            "success": "1",
            "year": year,
            "branch": branch,
            "section": section,
            "semester": semester,
            "data": subjects
        }, status=200)

    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"}, status=400)


@csrf_exempt
@ValidateAuthenticationToken
@api_view(["GET"])
def get_class_assignments_title(request, user=None):
    if user.user_type != 'teacher':
        return Response({
            "success": "3",
            "message": "Not authorized"
        }, status=401)

    try:
        year = request.GET.get('year')
        edu_year = request.GET.get('edu_year')
        branch = request.GET.get('branch')
        section = request.GET.get('section')
        subject = request.GET.get('subject')
        semester = request.GET.get('semester')
        assignment_title = request.GET.get('assignment_title')
        assignment_id = request.GET.get('assignment_id')  # question_id
        print(year, edu_year)
        class_obj = Class.objects.filter(
            edu_year=edu_year, year=year, branch=branch, section=section, semester=semester).first()

        if class_obj == None:
            return Response({"success": "0", "message": "No class found"}, status=404)

        assignment = Assignment.objects.filter(
            subject=subject, title=assignment_title, id=assignment_id).first()

        print('assignment', assignment)

        if assignment == None:
            return Response({"success": "0", "message": "No Assignment found for the subject"}, status=404)

        data = []
        color = Colors.objects.filter(subject=subject).first()
        assignmentAssigneds = AssignmentAssigned.objects.filter(
            class_obj=class_obj, assignment=assignment)
        for student_assignment in assignmentAssigneds:
            # student_assignment = AssignmentAssigned.objects.filter(assignment = assignment,student = student).first()
            # if not student_assignment.is_submitted:
            # 	continue
            temp = {}
            temp['title'] = assignment_title
            temp['id'] = student_assignment.id
            temp['student_id'] = student_assignment.student.id
            temp['student_roll_no'] = student_assignment.student.roll_no
            temp['subject'] = subject
            temp['subject_short_code'] = assignment.subject_code

            temp['student_name'] = student_assignment.student.name
            temp['due_date'] = assignment.due_date
            temp['creation_date'] = assignment.date
            temp['submission_date'] = student_assignment.date_submitted
            temp['submitted'] = student_assignment.is_submitted
            temp['marks'] = student_assignment.marks
            temp['feedback'] = student_assignment.feedback
            temp['answer_link'] = student_assignment.answer_link
            temp['assignment_link'] = assignment.assignment_link
            temp['assigned_by'] = assignment.assigned_by.name
            temp['color'] = color.color
            temp['gender'] = student_assignment.student.gender
            if student_assignment.is_submitted:
                if student_assignment.marks == None:
                    temp['status'] = 'submitted'
                else:
                    temp['status'] = 'reviewed'
            else:
                temp['status'] = 'pending'

            data.append(temp)

        print(982, len(data))

        return Response({
            "success": "1",
            "data": data
        }, status=200)

    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"}, status=400)


@csrf_exempt
@ValidateAuthenticationToken
@api_view(["GET"])
def get_class_assignments_title_report(request, user=None):
    if user.user_type != 'teacher':
        return Response({
            "success": "3",
            "message": "Not authorized"
        }, status=401)

    try:
        year = request.GET.get('year')
        edu_year = request.GET.get('edu_year')
        branch = request.GET.get('branch')
        section = request.GET.get('section')
        subject = request.GET.get('subject')
        semester = request.GET.get('semester')
        assignment_title = request.GET.get('assignment_title')
        assignment_id = request.GET.get('assignment_id')  # question_id

        class_obj = Class.objects.filter(
            edu_year=edu_year, year=year, branch=branch, section=section, semester=semester).first()

        if class_obj == None:
            return Response({"success": "0", "message": "No class found"}, status=404)

        students = Student.objects.filter(class_obj=class_obj)

        assignment = Assignment.objects.filter(
            subject=subject, title=assignment_title, id=assignment_id).first()

        if assignment == None:
            return Response({"success": "0", "message": "No Assignment found for the subject"}, status=404)

        data = []
        color = Colors.objects.filter(subject=subject).first()
        for student in students:
            student_assignment = AssignmentAssigned.objects.filter(
                assignment=assignment, student=student).first()
            # if not student_assignment.is_submitted:
            # 	continue
            temp = {}
            temp['title'] = assignment_title
            temp['id'] = student_assignment.id
            temp['student_id'] = student.id
            temp['student_roll_no'] = student.roll_no
            temp['subject'] = subject
            temp['subject_code'] = assignment.subject_code
            temp['student_name'] = student.name
            temp['due_date'] = assignment.due_date
            temp['creation_date'] = assignment.date
            temp['submission_date'] = student_assignment.date_submitted
            temp['submitted'] = student_assignment.is_submitted
            temp['marks'] = student_assignment.marks
            temp['feedback'] = student_assignment.feedback
            temp['answer_link'] = student_assignment.answer_link
            temp['assignment_link'] = assignment.assignment_link
            temp['assigned_by'] = assignment.assigned_by.name
            temp['color'] = color.color
            temp['gender'] = student.gender
            data.append(temp)

        row_labels = [
            # "Title",
            # "Subject",
            "Student_Roll",
            "Student Name",
            "Email",
            # "Due Date",
            # "Created",
            "IsSubmitted",
            "Submisstion Date",
            "Marks Awarded",
            "FeedBack Given",
            # "Assigned By",
            # "Assignment Link",
            "Submitted Link"
        ]
        workbook = xlsxwriter.Workbook(
            class_obj.edu_year + '-' +
            class_obj.branch + '-' +
            class_obj.section + '-' +
            subject + '-' + assignment_title +
            '.xls')

        worksheet = workbook.add_worksheet(assignment_title)
        bold = workbook.add_format({'bold': 1})

        merge_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'})

        row = 0
        col = 0
        worksheet.merge_range(row, col+2, row, col+5,
                              "Title : "+assignment_title, merge_format)
        row += 1
        worksheet.merge_range(row, col+2, row, col+5, "Subject : "+subject+'({section})'.format(section=class_obj.edu_year + '-' +
                                                                                                class_obj.branch + '-' +
                                                                                                class_obj.section), merge_format)
        row += 1
        worksheet.merge_range(row, col+2, row, col+5, "Due Date : " +
                              str(assignment.due_date).split(' ')[0], merge_format)
        row += 1
        worksheet.merge_range(row, col+2, row, col+5, "Created Date : " +
                              str(assignment.date).split(' ')[0], merge_format)
        row += 1
        worksheet.merge_range(row, col+2, row, col+5, "Assigned By : " +
                              str(assignment.assigned_by.name), merge_format)
        row += 1
        worksheet.merge_range(row, col+2, row, col+5, "", merge_format)
        worksheet.write_url(row, col+2, assignment.assignment_link)
        row += 5

        for index, i in enumerate(row_labels):
            worksheet.write(row, col+index, i, bold)
            worksheet.set_column(index+1, index+1, 25)
        row += 1
        col = 0
        for obj in data:
            # worksheet.write(row, col, obj['title'])
            # worksheet.write(row, col+1, obj['subject'])
            worksheet.write(row, col, obj['student_roll_no'])
            worksheet.write(row, col+1, obj['student_name'])
            worksheet.write(row, col+2, obj['student_roll_no']+'@vvit.net')
            # worksheet.write(row, col+5, str(obj['due_date']).split(' ')[0])
            # worksheet.write(row, col+6, str(obj['creation_date']).split(' ')[0])
            if obj['submitted']:
                z = 'True'
            else:
                z = 'False'
            worksheet.write(row, col+3, z)
            worksheet.write(
                row, col+4, str(obj['submission_date']).split(' ')[0])
            if obj['marks'] == None:
                z = '-'
            else:
                z = str(obj['marks'])
            worksheet.write(row, col+5, z + '/10')
            worksheet.write(row, col+6, obj['feedback'])
            # worksheet.write(row, col+11, obj['assigned_by'])
            # worksheet.write_url(row, col+12, obj['assignment_link'])
            if obj['answer_link'] == None:
                answer = 'None'
            else:
                answer = obj['answer_link']
            worksheet.write_url(row, col+7, answer)
            row += 1

        workbook.close()
        with open(class_obj.edu_year + '-' +
                  class_obj.branch + '-' +
                  class_obj.section + '-' +
                  subject + '-' + assignment_title +
                  '.xls', 'rb') as f:
            file_data = f.read()
        response = HttpResponse(
            file_data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="{}.xls"'.format(
            class_obj.edu_year + '-' + class_obj.branch + '-' + class_obj.section + '-' + subject + '-' + assignment_title)
        response['location'] = class_obj.edu_year + '-' + class_obj.branch + \
            '-' + class_obj.section + '-' + subject + '-' + assignment_title

        return response

    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"}, status=400)


@csrf_exempt
@ValidateAuthenticationToken
@api_view(["GET"])
def get_assignments_teachers(request, user=None):

    if user.user_type != 'teacher':
        return Response({
            "success": 0,
            "message": "You are not authorized to view these assignments"
        }, status=400)

    try:
        teacher = Teacher.objects.filter(user=user).first()

        if teacher == None:
            return Response({
                "success": 3,
                "message": "Something went wrong."
            }, status=403)

        assignments = Assignment.objects.filter(assigned_by=teacher)

        if len(assignments) == 0:
            return Response({
                "success": "1",
                "data": []
            })
        data = {}
        # print(assignments)
        for assignment in assignments:

            temp = {}

            assignmentAssigned = AssignmentAssigned.objects.filter(
                assignment=assignment).first()
            # print(assignmentAssigned)
            if assignmentAssigned == None:
                continue

            student = assignmentAssigned.student
            # print(student)
            if student == None:
                continue

            clas = assignment.class_obj
            print(clas)

            if clas == None:
                continue
            temp['id'] = assignment.id
            temp['due_date'] = assignment.due_date
            temp['creation_date'] = assignment.date
            temp['subject'] = assignment.subject
            temp['subject_code'] = assignment.subject_code
            color = Colors.objects.filter(subject=assignment.subject).first()
            temp['subject_color'] = color.color
            temp['question_link'] = assignment.assignment_link
            temp['assignment_title'] = assignment.title
            temp['year'] = clas.edu_year
            temp['branch'] = clas.branch
            temp['section'] = clas.section
            temp['semester'] = clas.semester
            # print(assignment.title)
            if assignment.title not in data:
                data[assignment.title] = temp

        return Response({
            "success": "1",
            "data": data
        }, status=200)

    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"}, status=400)


@csrf_exempt
@ValidateAuthenticationToken
@api_view(["POST"])
def extend_due_date(request, user=None):
    print(user)
    if user.user_type != 'teacher':
        return Response({
            "success": 0,
            "message": "You are not authorized to view these assignments"
        }, status=400)

    try:
        assignmentId = request.data['assignmentId']
        new_due_date = dt.parse(request.data['new_date']).replace(
            hour=0, minute=0, second=0)

        print(assignmentId, new_due_date)
        assignment = Assignment.objects.filter(id=assignmentId).first()
        print('start', new_due_date, assignment.date)
        if new_due_date < assignment.date:
            return Response({"success": "0", "message": "Due cannot be past"}, status=400)

        if assignment == None:
            return Response({"success": "0", "message": "No assignment found for this id."}, status=400)

        assignment.due_date = new_due_date

        assignment.save()

        return Response(({
            "success": "1",
            "message": "Due date extended."
        }), status=200)

    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"}, status=400)


@csrf_exempt
@ValidateAuthenticationToken
@api_view(["GET"])
def get_consolidation_for_student_by_sem(request, user=None):

    if user == None:
        return Response({
            "success": "0",
            "message": "User not found"
        }, status=400)

    try:

        roll_no = request.GET.get('roll_no')
        year = request.GET.get('year')
        edu_year = request.GET.get('edu_year')
        branch = request.GET.get('branch')
        section = request.GET.get('section')
        semester = request.GET.get('semester')

        student = Student.objects.filter(roll_no=roll_no).first()

        if student == None:
            return Response({
                "success": "0",
                "message": "Student not found"
            }, status=400)

        classs = Class.objects.filter(
            edu_year=edu_year, year=year, branch=branch, section=section, semester=semester).first()

        if classs == None:
            return Response({
                "success": "0",
                "message": "Class not found"
            }, status=400)

        studentsAssignments = AssignmentAssigned.objects.filter(
            student=student, class_obj=classs
        )
        data = {}
        for studentsAssignment in studentsAssignments:
            subject = studentsAssignment.assignment.subject
            if subject not in data:
                data[subject] = {}
            data[subject][studentsAssignment.assignment.title] = studentsAssignment.marks

        lectures = Lectures.objects.filter(class_obj=classs)
        print(lectures)
        for lecture in lectures:
            subject = lecture.subject
            if subject not in data:
                data[subject] = {}

        return Response({
            "success": "1",
            "data": data
        }, status=200)

    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"}, status=400)


@csrf_exempt
@ValidateAuthenticationToken
@api_view(["GET"])
def get_consolidation_for_student_sems(request, user=None):
    if user == None:
        return Response({
            "success": "0",
            "message": "User not found"
        }, status=400)
    try:

        roll_no = request.GET.get('roll_no')

        student = Student.objects.filter(roll_no=roll_no).first()

        if student == None:
            return Response({
                "success": "0",
                "message": "Student not found"
            }, status=200)

        studentAssigments = AssignmentAssigned.objects.filter(
            student=student)
        sems = []
        s = set()
        for studentAssigment in studentAssigments:
            classs = studentAssigment.class_obj

            temp = {}
            temp['year'] = classs.year
            temp['edu_year'] = classs.edu_year
            temp['branch'] = classs.branch
            temp['section'] = classs.section
            temp['semester'] = classs.semester

            temp['sem'] = str(classs)

            print(str(classs))
            if str(classs) not in s:
                s.add(str(classs))
                sems.append(temp)

        return Response({
            "success": "1",
            "data": sems
        }, status=200)

    except Exception as e:
        print(e)
        return Response({"success": "0", "message": "Something went wrong"}, status=200)
