#!/usr/bin/env python3
import onlinejudge.problem
import onlinejudge.implementation.utils as utils
import onlinejudge.implementation.logging as log
import re
import bs4
import requests
import urllib.parse
import json
import http.client # for the description string of status codes

class AtCoder(onlinejudge.problem.OnlineJudge):
    service_name = 'atcoder'

    def __init__(self, contest_id, problem_id):
        self.contest_id = contest_id
        self.problem_id = problem_id

    def download(self, session=None):
        url = self.get_url()
        log.status('GET: %s', url)
        resp = session.get(url)
        log.status(utils.describe_status_code(resp.status_code))
        msgs = self.get_messages_from_cookie(resp.cookies)
        for msg in msgs:
            log.status('message: %s', msg)
        if msgs:
            log.failure('interrupted')
            return []
        soup = bs4.BeautifulSoup(resp.content, 'lxml')
        samples = utils.SampleZipper()
        lang = None
        for pre, h3 in self.find_sample_tags(soup):
            s = utils.textfile(utils.dos2unix(pre.string.lstrip()))
            name = h3.string
            l = self.get_tag_lang(pre)
            if lang is None:
                lang = l
            elif lang != l:
                log.info('skipped due to language: current one is %s, not %s: %s ', lang, l, name)
                continue
            samples.add(s, name)
        return samples.get()

    def get_messages_from_cookie(self, cookies):
        msgtags = []
        for cookie in cookies:
            log.debug('cookie: %s', str(cookie))
            if cookie.name.startswith('__message_'):
                msg = json.loads(urllib.parse.unquote_plus(cookie.value))
                msgtags += [ msg['c'] ]
                log.debug('message: %s: %s', cookie.name, str(msg))
        msgs = []
        for msgtag in msgtags:
            soup = bs4.BeautifulSoup(msgtag, 'lxml')
            msg = None
            for tag in soup.find_all():
                if tag.string and tag.string.strip():
                    msg = tag.string
                    break
            if msg is None:
                log.error('failed to parse message')
            else:
                msgs += [ msg ]
        return msgs

    def get_tag_lang(self, tag):
        assert isinstance(tag, bs4.Tag)
        for parent in tag.parents:
            for cls in parent.attrs.get('class') or []:
                if cls.startswith('lang-'):
                    return cls

    def find_sample_tags(self, soup):
        result = []
        for pre in soup.find_all('pre'):
            log.debug('pre tag: %s', str(pre))
            if not pre.string:
                continue
            prv = utils.previous_sibling_tag(pre)
            if prv and prv.name == 'h3' and prv.string:  # AtCoder's javascript recognizes `h3+pre' as a sample input/output
                result += [( pre, prv )]
            else:
                if pre.parent and pre.parent.name == 'section':  # AtCoder's javascript sometimes fails. e.g. http://abc001.contest.atcoder.jp/tasks/abc001_1
                    prv = pre.parent and utils.previous_sibling_tag(pre.parent)
                    if prv and prv.name == 'h3' and prv.string:
                        result += [( pre, prv )]
        return result

    def get_url(self):
        return 'http://{}.contest.atcoder.jp/tasks/{}'.format(self.contest_id, self.problem_id)

    @classmethod
    def from_url(cls, s):
        m = re.match(r'^https?://([0-9A-Za-z-]+)\.contest\.atcoder\.jp/tasks/([0-9A-Za-z_]+)/?$', s)
        if m:
            return cls(m.group(1), m.group(2))

    def login(self, get_credentials, session=None):
        url = 'https://{}.contest.atcoder.jp/login'.format(self.contest_id)
        log.status('GET: %s', url)
        resp = session.get(url, allow_redirects=False)
        log.status(utils.describe_status_code(resp.status_code))
        msgs = self.get_messages_from_cookie(resp.cookies)
        for msg in msgs:
            log.status('message: %s', msg)
        if msgs:
            return 'login' not in resp.url
        username, password = get_credentials()
        log.status('POST: %s', url)
        resp = session.post(url, data={ 'name': username, 'password': password }, allow_redirects=False)
        msgs = self.get_messages_from_cookie(resp.cookies)
        for msg in msgs:
            log.status('message: %s', msg)
        return 'login' not in resp.url  # AtCoder redirects to the top page if success

onlinejudge.problem.list += [ AtCoder ]
