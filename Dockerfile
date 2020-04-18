FROM python:latest
RUN pip install requests github3.py
ADD . /slack-pull-reminder
WORKDIR /slack-pull-reminder
ENTRYPOINT python slack_pull_reminder.py
