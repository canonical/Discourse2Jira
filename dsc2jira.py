#!/usr/bin/env python3

from dsctriage import dsctriage
from datetime import datetime, timedelta, timezone

from jira import JIRA
import re, sys, os
import argparse
import json
import logging


# This script is used to automatically create Jira tickets
# 
# 1. download a list of forum topics from a single discourse category
# 2. open a local database file representing the same category
#    - this is to prevent duplicate tickets being created
# 3. if items exist in the downloaded list but not the db:
# 4.        create a jira issue for that item


class Configuration:
    def __init__(self, forum_url, forum_category, jira_server, jira_user, jira_api_token, database, dryrun, initdb):
        self.forum_url = forum_url
        self.forum_category = forum_category
        self.jira_server = jira_server
        self.jira_user =jira_user
        self.jira_api_token = jira_api_token
        self.database = database
        self.dryrun = dryrun
        self.initdb = initdb
    
def fetch_forum_topics(conf, start):

    logging.info("Downloading 'store-requests' discourse forum topics since {}".format(start))
    category = dsctriage.dscfinder.get_category_by_name(conf.forum_category, conf.forum_url)
    dsctriage.dscfinder.add_topics_to_category(category, start, conf.forum_url)

    logging.info("{} topics downloaded".format(category))

    return category

def parse_date_duration(date_param):
    # Parse the date parameter provided via command line
    if date_param.endswith('d'):
        days = int(date_param[:-1])
        delta = timedelta(days=days)
    elif date_param.endswith('w'):
        weeks = int(date_param[:-1])
        delta = timedelta(weeks=weeks)
    else:
        raise ValueError("Invalid date parameter. Please use syntax like '1d' or '2w'.")

    today = datetime.today().replace(tzinfo=timezone.utc)
    start_date = today - delta

    return start_date

def process_category(ctg):
    result_list = []
    for obj in ctg._topics:
        result_list.append({"id": obj._id, "slug": obj._slug, "jira": "false", "url": "https://forum.snapcraft.io/t/{}/{}/".format(obj._slug, obj._id)})
    return result_list


def import_json_db(filename):
    with open(filename, "r") as json_file:
        try:
            my_list = json.load(json_file)
        except json.JSONDecodeError:
            return []
    return my_list


def create_issue(config, project, summary, desc, issuetype, component):
    issue_dict = {
        'project': {'key': project},
        'summary':  summary,
        'description': desc,
        'issuetype': {'name': issuetype},
        'components': [{'name': component}],
        'duedate': (datetime.date(datetime.today()) + timedelta(days=7)).isoformat()
    }
    issue = 0
    if not config.dryrun and not config.initdb:
        issue = jira.create_issue(fields=issue_dict)
        logging.info("creating ticket: {}, {}".format(issue, issue_dict["summary"]))
        return issue
    else:
        logging.info("[DRY RUN] creating ticket: {}, {}".format(issue, issue_dict["summary"]))
        return "skip"
    


def main(conf, start_date):

    # use dsc to grab all the topics in the store category from the forum
    category = fetch_forum_topics(conf, start_date)

    # extract just the elements we need from dsc's category object
    forum_topics = process_category(category)

    # open the database file
    # TODO: make this a parameter
    database_list = import_json_db(conf.database)

    # this list represents items found in the forum that are NOT already in the db
    new_list = []

    logging.debug("iterating through forum topics")

    # high level logic below is:
    # iterate through forum topics
    #  iterate through database
    #   if not found, create new issue and entry in new_list (to be added to db)
    #
    # there's an additional check for db items without jira entries already, this is for initial setup
    # and would not usually be expected to be taken
    
    #in order to accurately track the number of items in the db (when Found = True) that also need a
    # jira issue created for them (where Jira="0"), we use this variable
    updated_items_cnt = 0   

    for forum_topic in forum_topics:
        found = False
        logging.debug("topic: {}".format(forum_topic["slug"]))
        for db_entry in database_list:
            if forum_topic["id"] == db_entry["id"]:
                found = True
                logging.debug("found a matching topic in the db")
                if db_entry["jira"] == "0":
                    # this is for the case when an entry exists in the db but not in Jira
                    issue = create_issue(conf, 'SEC', forum_topic["slug"], "https://forum.snapcraft.io/t/{}/{}/".format(forum_topic["slug"], forum_topic["id"]), 'Story', "Snap Review")
                    #also need to update the db
                    db_entry["jira"] = str(issue)
                    updated_items_cnt = updated_items_cnt+1
                else:
                    # this is the usual case, just log it
                    logging.debug("item already in database with jira ticket: {}, {}".format(db_entry["slug"], db_entry["jira"]))
                break
        if found == False:
            # this is the case for forum topics that aren't in the database
            issue = create_issue(conf, 'SEC', forum_topic["slug"], "https://forum.snapcraft.io/t/{}/{}/".format(forum_topic["slug"], forum_topic["id"]), 'Story', "Snap Review")
            new_list.append({"id": forum_topic["id"], "slug": forum_topic["slug"], "jira": str(issue), "url": "https://forum.snapcraft.io/t/{}/{}/".format(forum_topic["slug"], forum_topic["id"])})

    # finished processing the forum topics so add the new list to the existing database
    for i in new_list:
        database_list.append(i)

    if not conf.dryrun and not conf.initdb:
        logging.info("Created {} Jira entries".format(len(new_list) + updated_items_cnt))
    else:
        logging.info("[DRY RUN] Created {} Jira entries".format(len(new_list) + updated_items_cnt))

    #save the database
    if not conf.dryrun:
        with open(conf.database, "w") as json_file:
            json.dump(database_list, json_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='ForumSync', description='Check that discourse topics have a matching Jira card.')
    parser.add_argument('-n', '--dry-run', dest='dryrun', help='Dry run. Do not perform any jira ticket creation or database writes', action='store_true')
    parser.add_argument('-i', '--init-db', dest='initdb', help='Create database records for fetched topics, but do not create Jira entries', action='store_true')
    parser.add_argument('-d', '--duration', help='Date period to search back through (relative to now, eg: 1d, 2w)', default='7d')
    parser.add_argument('-f', '--database', type=str, dest='db_file', help='Optional database file (default=forum_db.json)', default='forum_db.json')
    parser.add_argument('-c', '--config', help='forum and jira configuration details file (default=config.json)', default='config.json')
    parser.add_argument('-l', '--loglevel', type=str, help='Log level', default='INFO', choices=['INFO', 'DEBUG', 'WARN', 'ERROR'])
    args = parser.parse_args()

    numeric_level = getattr(logging, args.loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    logging.basicConfig(level=numeric_level)

    if args.dryrun and args.initdb:
        logging.error("--dry-run and --init-db are mutually exclusive")
        sys.exit(-1)


    if os.access(args.db_file, os.W_OK):
        pass
    else:
        logging.error("database file not does not exist or is not writable: {}".format(args.db_file))
        sys.exit(-1)

    start_date = parse_date_duration(args.duration)
    logging.info(f"{start_date}")
    logging.debug("Using {} time period".format(args.duration))


    config = import_json_db(args.config)
        
    conf = Configuration(
        forum_url = config["forum_url"],
        forum_category = config["forum_category"],
        jira_server = config["jira_server"],
        jira_user = config["jira_user"],
        jira_api_token= config["jira_api_token"],
        database = args.db_file,
        dryrun = args.dryrun,
        initdb = args.initdb
    )

    # initialize our Jira connection
    jira = JIRA(server=conf.jira_server, basic_auth=(conf.jira_user, conf.jira_api_token))

    main(conf, start_date)

