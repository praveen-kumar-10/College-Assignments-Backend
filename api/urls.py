from django.urls import path
from .views import *

urlpatterns = [
    path('approve', handle_approve),#done
    path('create-bulk-students', createBulkStudents),#done
    path('create-assignment',create_assignment),#done
    path('create-subjects',createBulkSubjects),#done
    path('students/assignments',get_assignment_students),#done
    path('students/assignments/<int:id>',get_student_assignment_id),
    path('students/upload',submit_assignment),#done
    path('checkadmin',check_admin),#done
    path('getteachers',get_teachers),#done
    path('assign-marks',assign_marks_feedback),#done
    # path('all-assignments',get_batches_branch_classes),
    path('class-assignments-details',get_class_assignments_details),#done,
    path('get-branches-by-year',get_branches_by_year),
    path('get-sections-by-branch-year',get_sections_by_branches_year),
    # path('get-students-by-branch-year-section',get_students_by_branch_year_section),
    path('get-subject-by-branch-year-section-sem',get_subject_by_branch_year_section_sem),
    path('get-class-assignments-title',get_class_assignments_title),
    path('get-class-assignments-title-report',get_class_assignments_title_report),
    path('my-assignment-teacher',get_assignments_teachers),
    path('get-student-consolidation-sems',get_consolidation_for_student_sems),
    path('get-student-consolidation-by-sem',get_consolidation_for_student_by_sem),
    path('promote_students_by_year',promote_student),
    path('promote_students_by_year_confirm',promote_student_confirm),
    path('extend-due-date',extend_due_date),

]