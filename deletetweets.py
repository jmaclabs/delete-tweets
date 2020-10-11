#!/usr/bin/env python

import argparse
import io
import os
import sys
import time
import json
import yaml

import twitter
from dateutil.parser import parse

__author__ = "Koen Rouwhorst"
__maintainer__ = "John McLaughlin"
__version__ = "1.0.1"


class TweetDestroyer(object):
    def __init__(self, twitter_api):
        self.twitter_api = twitter_api

    def destroy(self, tweet_id):
        try:
            print("delete tweet %s" % tweet_id)
            self.twitter_api.DestroyStatus(tweet_id)
            # NOTE: A poor man's solution to honor Twitter's rate limits.
            time.sleep(0.5)
        except twitter.TwitterError as err:
            print("Exception: %s\n" % err.message)


class TweetReader(object):
    def __init__(self, reader, date=None, restrict=None):
        self.reader = reader
        if date is not None:
            self.date = parse(date, ignoretz=True).date()
        self.restrict = restrict

    def read(self):
        for row in self.reader:
            if row.get("created_at", "") != "":
                tweet_date = parse(row["created_at"], ignoretz=True).date()
                if self.date != "" and \
                        self.date is not None and \
                        tweet_date >= self.date:
                    continue

            if (self.restrict == "retweet" and
                    not row.get("full_text").startswith("RT @")) or \
                    (self.restrict == "reply" and
                     row.get("in_reply_to_user_id_str") == ""):
                continue

            yield row


def delete(tweetjs_path, date, r, creds):
    with io.open(tweetjs_path, mode="r", encoding="utf-8") as tweetjs_file:
        count = 0

        api = twitter.Api(consumer_key=creds["secrets"]["TWITTER_CONSUMER_KEY"],
                          consumer_secret=creds["secrets"]["TWITTER_CONSUMER_SECRET"],
                          access_token_key=creds["secrets"]["TWITTER_ACCESS_TOKEN"],
                          access_token_secret=creds["secrets"]["TWITTER_ACCESS_TOKEN_SECRET"])
        destroyer = TweetDestroyer(api)

        tweets = json.loads(tweetjs_file.read()[25:])
        for row in TweetReader(tweets, date, r).read():
            if "id_str" not in row["tweet"]:
                print("DAFUQ: {}".format(row))
                exit(1)
            destroyer.destroy(row["tweet"]["id_str"])
            count += 1

        print("Number of deleted tweets: %s\n" % count)


def main():
    parser = argparse.ArgumentParser(description="Delete old tweets.")
    parser.add_argument("-d", dest="date", required=True,
                        help="Delete tweets until this date")
    parser.add_argument("-r", dest="restrict", choices=["reply", "retweet"],
                        help="Restrict to either replies or retweets")
    parser.add_argument("file", help="display a square of a given number",
                        type=str)

    args = parser.parse_args()

    if not os.path.isfile("conf/creds.yml"):
        sys.stderr.write("Twitter API credentials file 'conf/creds.yml' not found.")
        exit(1)

    with open("conf/creds.yml", 'r') as stream:
        try:
            creds = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    delete(args.file, args.date, args.restrict, creds)


if __name__ == "__main__":
    main()
