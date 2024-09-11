import pronotepy
import datetime


def get_homeworks(client: pronotepy.Client, date: datetime.date) -> list[dict]:
  homeworks = []
  for homework in client.homework(date):
    homeworks.append({
        "subject": homework.subject.name,
        "description": homework.description,
        "date": homework.date.strftime("%d/%m/%Y"),
        "background_color": homework.background_color,
        "done": homework
    })
  return homeworks


def get_grades(client: pronotepy.Client,
               date: datetime.date) -> list[pronotepy.Grade]:
  grades = client.current_period.grades
  return grades
