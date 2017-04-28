#!/usr/bin/env python

import argparse
import re
import json
import urllib2
from urlparse import urlparse
from minio import Minio
import requests
import polling
import logging


logging.getLogger("requests").setLevel(logging.WARNING)
parser = argparse.ArgumentParser()
parser.add_argument("--repeat", type=int, default=1)
parser.add_argument("--server", default="http://localhost:8000")
parser.add_argument("--wait", action="store_true")
parser.add_argument("task")


class TES:

    def __init__(self,
                 url,
                 s3_endpoint=None,
                 s3_access_key=None,
                 s3_secret_key=None):
        self.url = url
        self.s3_endpoint = s3_endpoint
        self.s3_access_key = s3_access_key
        self.s3_secret_key = s3_secret_key

    def get_service_info(self):
        req = urllib2.Request("%s/v1/tasks/service-info" % (self.url))
        u = urllib2.urlopen(req)
        return json.loads(u.read())

    def s3connect(self):
        n = urlparse(self.s3_endpoint)
        tls = None
        if n.scheme == "http":
            tls = False
        if n.scheme == "https":
            tls = True
        minioClient = Minio(
            n.netloc,
            access_key=self.s3_access_key,
            secret_key=self.s3_secret_key,
            secure=tls
        )
        return minioClient

    def upload_file(self, path, storage):
        n = urlparse(storage)
        if n.scheme != "s3":
            raise Exception("Not S3 URL")
        c = self.s3connect()
        object_name = n.path
        object_name = re.sub("^/", "", object_name)
        c.fput_object(n.netloc, object_name, path)

    def download_file(self, path, storage):
        n = urlparse(storage)
        if n.scheme != "s3":
            raise Exception("Not S3 URL")
        c = self.s3connect()
        object_name = n.path
        object_name = re.sub("^/", "", object_name)
        c.fget_object(n.netloc, object_name, path)

    def list(self, bucket):
        c = self.s3connect()
        for i in c.list_objects(bucket):
            yield "s3://%s/%s" % (bucket, i.object_name)

    def make_bucket(self, bucket):
        c = self.s3connect()
        c.make_bucket(bucket)

    def bucket_exists(self, bucket):
        c = self.s3connect()
        c.bucket_exists(bucket)

    def submit(self, task):
        req = urllib2.Request("%s/v1/tasks" % (self.url))
        u = urllib2.urlopen(req, json.dumps(task))
        data = json.loads(u.read())
        task_id = data['id']
        return task_id

    def wait(self, task_id, timeout=10):
        def check_success(data):
            return data["state"] not in ['QUEUED', "RUNNING", "INITIALIZING"]
        return polling.poll(
            lambda: self.get_task(task_id),
            check_success=check_success,
            timeout=timeout,
            step=0.1)

    def get_task(self, task_id):
        return requests.get("%s/v1/tasks/%s" % (self.url, task_id)).json()

    def cancel_task(self, task_id):
        return requests.post(
            "%s/v1/tasks/%s:cancel" % (self.url, task_id)
        ).json()


if __name__ == '__main__':
    args = parser.parse_args()
    c = TES(args.server)
    t = json.load(open(args.task))

    task_ids = []
    for i in range(args.repeat):
        task_id = c.submit(t)
        task_ids.append(task_id)

    if args.wait:
        for task_id in task_ids:
            c.wait(task_id)