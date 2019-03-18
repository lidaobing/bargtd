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
            return Profile.from_map([x for x in self.data['profiles'] if x['name'] == self.data['current_profile']])
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
        if 'engine' in m:
            res.engine = m['engine']
        if 'user' in m:
            res.user = m['user']
        if 'repo' in m:
            res.repo = m['repo']
        if 'auth' in m:
            res.auth = m['auth']
        return res

class Task:
    def __init__(self, number, title, url, assignee):
        self.number = number
        self.title = title
        self.url = url
        self.assignee = assignee


class GithubEngine:
    def __init__(self, profile):
        self.profile = profile

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



def get_all_tasks(profile):
    assert profile.engine == 'github'
    engine = GithubEngine(profile)
    return engine.get_all_tasks()

def main():
    profile = None
    config_path = os.path.expanduser('~/.bargtd.json')
    config = None
    if os.path.exists(config_path):
        config = Config(open(config_path))
        profile = config.get_current_profile()
    if profile is None:
        profile = Profile()
    tasks = get_all_tasks(profile)
    assigned_tasks = [x for x in tasks if x.assignee is not None]
    unassigned_tasks = [x for x in tasks if x.assignee is None]
    profiles = []
    if config is not None:
        profiles = config.get_profile_names()
    print('🤹(%d/%d)' % (len(assigned_tasks), len(unassigned_tasks)))
    print('---')
    print('Tools')
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
