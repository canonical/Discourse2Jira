# Discourse2Jira

## About

This project is built specifically to automate the creation of Jira issues
for each new topic in the 'store-requests' category of forum.snapcraft.io

Some of it has been generalised, but there are many elements of it that are
specific to that use case.

Included is code from lvoytek's [dsctriage](https://github.com/lvoytek/discourse-triage). Thanks Lena.

## Install / Quickstart

1. Clone the repo:
```
    $ git clone git@github.com:dclane-code/Discourse2Jira.git
```
2. Create a virtual env and install jira module
```
    $ cd Discourse2Jira
    $ python3 -m venv env
    $ . env/bin/activate
    $ pip3 install jira
```
3. Create a config file
```
    $ cp example_config.json config.json
    [edit config.json in your favourite editor]
```
4. Insert a Jira API token into your config.

In order to be able to post to Jira, the script needs some credentials. Use an API token that you can generate here
```
    https://id.atlassian.com/manage-profile/security/api-tokens
```
5. Create an empty database
```
   $ touch forum_db.json
```
6. Run (see (initial setup)[#initial-setup] below before removing '-n')
```
    $ ./dsc2jira.py -n  # dry run, see what might happen
```

## The database format

Each discourse topic is represented in a json 'database' file by default called `forum_db.json`.

The format for each topic is
```
{
    "id": 36045,
    "slug": "request-for-a-new-pc-gadget-snap-track-classic-23-10",
    "jira": "SEC-2457",
    "url": "https://forum.snapcraft.io/t/request-for-a-new-pc-gadget-snap-track-classic-23-10/36045/"
}
```
**Important** If a topic does not exist in the database, or has `"jira": "0"`, then a Jira issue will be created for it.

### Initial setup

To avoid unnecessary Jira issue creation on first run (with an empty database), you should perform a database initialization with:
```
$ ./dsc2jira.py -i
```
- This will produce a `forum_db.json` that has 0's for each Jira entry (instead of actual Jira issue numbers).
- Inspect the database file and the forum manually and for any forum topics that already have Jira issues:
    - Replace the "0" with a non-zero value (preferably the Jira issue number, but any non-zero value will suffice).
- This will prevent Discourse2Jira creating a new Jira issue for that topic. Issues created by Discourse2Jira will have that field populated with their Jira issue number, as per the example above (`SEC-2457')

A sed one-liner to avoid update the database file so that NO new issues get created:
```
sed -i 's/\"0\"/\"skip\"/g' forum_db.json
```


## Search period

By default, Discourse2Jira searches for forum topics back 7-days from `now()`. This can be overriden with the `-d` argument, eg: `./dsc2jira.py -d 4w` to create Jira cards for the last 4 weeks worth of forum topics









