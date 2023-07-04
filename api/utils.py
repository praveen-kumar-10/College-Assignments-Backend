from django.template.loader import render_to_string
from django.utils.html import strip_tags

import pytz


from datetime import *
import dateutil.parser as dt

def get_email_description(context,template_name):

    html = render_to_string(template_name+".html", context)
    
    text = strip_tags(html)

    return [html,text]

def get_days_before_due_date(creation_date,due_date):
    india = pytz.timezone('Asia/Kolkata')
    due_date = due_date.astimezone(india)
    creation_date = creation_date.astimezone(india)
    z = due_date-creation_date-timedelta(days=1)
    days = creation_date+z -creation_date
    return days.days

# get_days_before_due_date("2022-11-05T23:11:26Z","2022-11-07T23:11:26Z")
