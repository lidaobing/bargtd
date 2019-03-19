#!/usr/bin/env /usr/local/bin/python3

import netrc
import requests
import json
import os.path

class Config:
    def __init__(self, ifile):
        self.data = json.loads(ifile.read())

    def get_profile_names(self):
        return [x['name'] for x in self.data['profiles']]

    def get_current_profile(self):
        if 'current_profile' in self.data:
            return Profile.from_map([x for x in self.data['profiles'] if x['name'] == self.data['current_profile']][0])
        else:
            return Profile.from_map(self.data['profiles'][0])

class Profile:
    def __init__(self):
        self.engine = 'github'
        self.user = 'lidaobing'
        self.repo = 'private'
        self.auth = 'netrc'

    @staticmethod
    def from_map(m):
        res = Profile()
        res.__dict__.update(m)
        return res

class Task:
    def __init__(self, number, title, url, assignee):
        self.number = number
        self.title = title
        self.url = url
        self.assignee = assignee

class Engine:
    def get_all_tasks(self):
        page = 1
        res = []
        while True:
            tasks = self.get_tasks_for_page(page)
            if len(tasks) == 0:
                break
            res.extend(tasks)
            page += 1
        return res

    def get_tasks_for_page(self, page):
        raise NotImplementedError

    def get_create_url(self):
        raise NotImplementedError

class GithubEngine(Engine):
    def __init__(self, profile):
        self.profile = profile

    def get_tasks_for_page(self, page):
        assert self.profile.auth == 'netrc'
        a = netrc.netrc()
        username, _, password = a.authenticators('api.github.com')

        url = "https://api.github.com/repos/%s/%s/issues?page=%s" % (self.profile.user, self.profile.repo, page)
        response = requests.get(url, auth=(username, password))
        response.raise_for_status()
        content = response.content
        j = json.loads(content)
        res = []
        for j0 in j:
            assignee = None
            if j0['assignee'] is not None:
                assignee = j0['assignee']
            res.append(Task(j0['number'], j0['title'], j0['html_url'], assignee))
        return res

    def get_create_url(self):
        return "https://github.com/%s/%s/issues/new" % (self.profile.user, self.profile.repo)

class GitlabEngine(Engine):
    def __init__(self, profile):
        self.profile = profile

    def get_tasks_for_page(self, page):
        entry = self.profile.entry
        project_id = self.profile.project_id
        token = self.profile.token
        # FIXME: urlencode
        url = "%s/api/v4/projects/%s/issues?state=opened&private_token=%s&page=%s" % (entry, project_id, token, page)
        response = requests.get(url)
        response.raise_for_status()
        content = response.content
        j = json.loads(content)
        res = []
        for j0 in j:
            assignee = None
            if j0['assignee'] is not None:
                assignee = j0['assignee']
            res.append(Task(j0['iid'], j0['title'], j0['web_url'], assignee))
        return res

    def get_create_url(self):
        return "%s/%s/%s/issues/new" % (self.profile.entry, self.profile.user, self.profile.repo)

def get_engine(profile):
    if profile.engine == 'github':
        return GithubEngine(profile)
    if profile.engine == 'gitlab':
        return GitlabEngine(profile)
    raise Exception("unknown engine: " + profile.engine)

def main():
    profile = None
    config_path = os.path.expanduser('~/.bargtd.json')
    config = None
    if os.path.exists(config_path):
        config = Config(open(config_path))
        profile = config.get_current_profile()
    if profile is None:
        profile = Profile()
    engine = get_engine(profile)
    tasks = engine.get_all_tasks()
    assigned_tasks = [x for x in tasks if x.assignee is not None]
    unassigned_tasks = [x for x in tasks if x.assignee is None]
    profiles = []
    if config is not None:
        profiles = config.get_profile_names()
    print('🤹(%d/%d)' % (len(assigned_tasks), len(unassigned_tasks)))
    print('---')
    print('Tools')
    print('--New Task | href=%s' % engine.get_create_url())
    print('--Refresh | refresh=true')
    print('--Profiles')
    for x in profiles:
        print('----%s | refresh=true' % x)
    print('---')
    for x in assigned_tasks:
        print("#%s: %s | href=%s" % (x.number, x.title, x.url))
    print('---')
    for x in unassigned_tasks:
        print("#%s: %s | href=%s length=30" % (x.number, x.title, x.url))

if __name__ == '__main__':
    main()
