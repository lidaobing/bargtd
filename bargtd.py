#!/usr/local/bin/python3

import netrc
import requests
import json
import os.path
import urllib.parse

# priority: ⬆️🔼⏹🔽⬇️

class Config:
    def __init__(self, ifile):
        self.data = json.loads(ifile.read())

    def get_profile_by_name(self, name):
        return Profile.from_map([x for x in self.data['profiles'] if x['name'] == name][0])

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
    def __init__(self, number, title, url, assignee, prefix = ''):
        self.number = number
        self.title = title
        self.url = url
        self.assignee = assignee
        self.prefix = prefix

class Engine:
    def __init__(self):
        self.prefix = ''

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

class MergeEngine(Engine):
    def __init__(self, profile, config):
        super().__init__()
        self.profile = profile
        self.engines = []
        for x in profile.engines:
            engine = get_engine(config.get_profile_by_name(x), config)
            engine.prefix = x
            self.engines.append(engine)

    def get_create_url(self):
        pass

    def get_all_tasks(self):
        tasks = []
        for x in self.engines:
            tasks += x.get_all_tasks()
        return tasks

class GithubEngine(Engine):
    def __init__(self, profile):
        super().__init__()
        self.profile = profile

    def get_tasks_for_page(self, page):
        assert self.profile.auth == 'netrc'
        a = netrc.netrc()
        username, _, password = a.authenticators('api.github.com')

        url = "https://api.github.com/repos/%s/%s/issues?page=%s" % (self.profile.user, self.profile.repo, page)
        response = None
        try:
            response = requests.get(url, auth=(username, password))
        except Exception as e:
            raise Exception("fail to get url %s: %s" % (url, e)) from None
        response.raise_for_status()
        content = response.content
        j = json.loads(content)
        res = []
        for j0 in j:
            assignee = None
            if j0['assignee'] is not None:
                assignee = j0['assignee']
            res.append(Task(j0['number'], j0['title'], j0['html_url'], assignee, self.prefix))
        return res

    def get_create_url(self):
        return "https://github.com/%s/%s/issues/new" % (self.profile.user, self.profile.repo)

class GitlabEngine(Engine):
    def __init__(self, profile):
        super().__init__()
        self.profile = profile

    def get_tasks_for_page(self, page):
        entry = self.profile.entry
        project_id = self.profile.project_id
        token = self.profile.token
        url = "%s/api/v4/projects/%s/issues?%s" % (
            entry,
            project_id,
            urllib.parse.urlencode({'state': 'opened', 'private_token': token, 'page': page})
        )
        response = None
        try:
            response = requests.get(url)
        except Exception as e:
            raise Exception("fail to get url %s: %s" % (url, e)) from None
        response.raise_for_status()
        content = response.content
        j = json.loads(content)
        res = []
        for j0 in j:
            assignee = None
            if j0['assignee'] is not None:
                assignee = j0['assignee']
            res.append(Task(j0['iid'], j0['title'], j0['web_url'], assignee, self.prefix))
        return res

    def get_create_url(self):
        return "%s/%s/%s/issues/new" % (self.profile.entry, self.profile.user, self.profile.repo)

class JiraEngine(Engine):
    def __init__(self, profile):
        super().__init__()
        self.profile = profile

    def get_tasks_for_page(self, page):
        host = self.profile.host
        project = self.profile.project
        https = self.profile.https
        me = self.profile.assignee


        assert self.profile.auth == 'netrc'
        a = netrc.netrc()
        username, _, password = a.authenticators(host)

        # FIXME: jql encode
        url = "%s://%s/rest/api/2/search?%s" % (
            'https' if https else 'http',
            host,
            urllib.parse.urlencode({'jql': 'project=%s AND resolution = Unresolved' % project, 'startAt': (page-1)*50, 'maxResults':50}))
        response = None
        try:
            response = requests.get(url, auth=(username, password))
        except Exception as e:
            raise Exception("fail to get url %s: %s" % (url, e)) from None
        response.raise_for_status()
        content = response.content
        # print repr(content)
        j = json.loads(content)
        res = []
        for j0 in j['issues']:
            assignee = None
            if j0['fields']['assignee'] is not None:
                assignee = j0['fields']['assignee']['key']
                if assignee != me:
                    assignee = None
            web_url = '%s://%s/browse/%s' % ('https' if https else 'http', host, j0['key'])
            res.append(Task(j0['key'], j0['fields']['summary'], web_url, assignee, self.prefix))
        return res

    def get_create_url(self):
        return "%s://%s" % ('https' if self.profile.https else 'http', self.profile.host)

def get_engine(profile, config):
    if profile.engine == 'github':
        return GithubEngine(profile)
    if profile.engine == 'gitlab':
        return GitlabEngine(profile)
    if profile.engine == 'merge':
        return MergeEngine(profile, config)
    if profile.engine == 'jira':
        return JiraEngine(profile)
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
    engine = get_engine(profile, config)
    tasks = engine.get_all_tasks()
    assigned_tasks = [x for x in tasks if x.assignee is not None]
    unassigned_tasks = [x for x in tasks if x.assignee is None]
    profiles = []
    if config is not None:
        profiles = config.get_profile_names()
    print('🤹(%d/%d)' % (len(assigned_tasks), len(unassigned_tasks)))
    print('---')
    print('New Task | href=%s' % engine.get_create_url())
    print('Tools')
    print('--Refresh | refresh=true')
    print('--Profiles')
    for x in profiles:
        print('----%s | refresh=true' % x)
    print('---')
    for x in assigned_tasks:
        print("%s#%s: %s | href=%s" % (x.prefix, x.number, x.title, x.url))
    print('---')
    for x in unassigned_tasks:
        print("%s#%s: %s | href=%s length=30" % (x.prefix, x.number, x.title, x.url))

if __name__ == '__main__':
    main()
