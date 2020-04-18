import os
import sys

import requests
from github3 import login

POST_URL = 'https://slack.com/api/chat.postMessage'

ignore = os.environ.get('IGNORE_WORDS')
IGNORE_WORDS = [i.lower().strip() for i in ignore.split(',')] if ignore else []

repositories = os.environ.get('REPOSITORIES')
REPOSITORIES = [r.lower().strip() for r in repositories.split(',')] if repositories else []

usernames = os.environ.get('USERNAMES')
USERNAMES = [u.lower().strip() for u in usernames.split(',')] if usernames else []

SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', '#general')

try:
    SLACK_API_TOKEN = os.environ['SLACK_API_TOKEN']
    GITHUB_API_TOKEN = os.environ['GITHUB_API_TOKEN']
    ORGANIZATION = os.environ['ORGANIZATION']
except KeyError as error:
    sys.stderr.write('Please set the environment variable {0}'.format(error))
    sys.exit(1)

INITIAL_MESSAGE = """\
Hi! There's a few open pull requests you should take a \
look at:

"""


def fetch_repository_pulls(repository):
    pulls = []
    for pull in repository.pull_requests():
        if pull.state == 'open' and (not USERNAMES or pull.user.login.lower() in USERNAMES):
            pulls.append(pull)
    return pulls


def is_valid_title(title):
    lowercase_title = title.lower()
    for ignored_word in IGNORE_WORDS:
        if ignored_word in lowercase_title:
            return False

    return True


def format_pull_requests(pull_requests, owner, repository):
    lines = []
    creators = {}
    approved_creators = {}

    for pull in pull_requests:
        approval_details = { 'count': 0, 'reviewers': [] }
        if is_valid_title(pull.title):
            creator = pull.user.login
            reviews = pull.reviews().__iter__()

            for review in reviews:
                if review.state == "APPROVED":
                    approval_details['count'] += 1
                    approval_details['reviewers'].append(review.user.login)

                if approval_details['count'] == 2:
                    approved_string = '*[{0}/{1}]* <{2}|{3}> : APPROVED BY {4} '.format(
                        owner, repository, pull.html_url, pull.title, ','.join(approval_details['reviewers']))
                    if creator in approved_creators:
                        approved_creators[creator].append(approved_string)
                    else:
                        approved_creators[creator] = [ approved_string ]
                    break

            if approval_details['count'] < 2:
                line = '*[{0}/{1}]* <{2}|{3}> '.format(
                    owner, repository, pull.html_url, pull.title)
                if creator in creators:
                    creators[creator].append(line)
                else:
                    creators[creator] = [ line ]

    for creator in creators:
        creator_text = ">*AUTHOR* : *_%s_* :arrow_right: *Count : %s*\n"%(
            creator, str(len(creators[creator]))) + '\n'.join(creators[creator])
        lines.append(creator_text)

    heading = "\n*#############################################################################################*"
    heading += "\n*############################ APPROVED PULL REQUESTS #########################################*"
    heading += "\n*#############################################################################################*\n"
    lines.append(heading)

    for creator in approved_creators:
        approved_text = ">*AUTHOR* : *_%s_* :arrow_right: *Count : %s*\n"%(
                    creator, str(len(approved_creators[creator]))) + '\n'.join(approved_creators[creator])
        lines.append(approved_text)

    return lines


def fetch_organization_pulls(organization_name):
    """
    Returns a formatted string list of open pull request messages.
    """
    client = login(token=GITHUB_API_TOKEN)
    organization = client.organization(organization_name)
    lines = []

    for repository in organization.repositories():
        if REPOSITORIES and repository.name.lower() not in REPOSITORIES:
            continue
        unchecked_pulls = fetch_repository_pulls(repository)
        lines += format_pull_requests(unchecked_pulls, organization_name,
                                      repository.name)

    return lines


def send_to_slack(text):
    payload = {
        'token': SLACK_API_TOKEN,
        'channel': SLACK_CHANNEL,
        'username': 'Pull Request Reminder',
        'icon_emoji': ':bell:',
        'text': text
    }

    response = requests.post(POST_URL, data=payload)
    answer = response.json()
    if not answer['ok']:
        raise Exception(answer['error'])


def cli():
    lines = fetch_organization_pulls(ORGANIZATION)
    if lines:
        text = INITIAL_MESSAGE + '\n'.join(lines)
        print(text)
#         send_to_slack(text)

if __name__ == '__main__':
    cli()
