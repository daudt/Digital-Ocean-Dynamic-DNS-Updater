#!/usr/bin/python
# Original Script by Michael Shepanski (2013-08-01)
# Updated to use DigitalOcean API v2

import json
import re
import urllib2
from datetime import datetime
import argparse

# Parse the command line arguments (all required or else exception will be thrown)
parser = argparse.ArgumentParser()
parser.add_argument('-k', '--key', help='Digital Ocean API key', required=True)
parser.add_argument('-d', '--domain', help='Domain name the record belongs to.', required=True)
parser.add_argument('-r', '--record', help='Subdomain record to be updated.', required=True)
parser.add_argument('-t', '--type', help='Record type (e.g.: A or AA).', required=True)
args = parser.parse_args()

# assign the parsed args to their respective variables
KEY = args.key
DOMAIN = args.domain
RECORD = args.record
RTYPE = args.type

CHECKIPv4 = "http://checkip.dyndns.org:8245"
IPv4_REGEX = '(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
CHECKIPv6 = "http://checkipv6.dyndns.org:8245"
IPv6_REGEX = '(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]'\
             '{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}'\
             '|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}'\
             '|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4})'\
             '{0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}'\
             '(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9])'\
             '{0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))'
APIURL = "https://api.digitalocean.com/v2"
AUTH_HEADER = {'Authorization': "Bearer %s" % KEY}


def get_external_ip():
    """ Return the current external IP. """
    if RTYPE == 'A':
        fp = urllib2.urlopen(CHECKIPv4)
        html = fp.read().decode("utf8")
        ipregex = re.compile(IPv4_REGEX)
    elif RTYPE == 'AAAA':
        fp = urllib2.urlopen(CHECKIPv6)
        html = fp.read().decode("utf8")
        ipregex = re.compile(IPv6_REGEX)
    else:
        return False
    """ Parse the ip addresses """
    external_ip = ipregex.search(html)
    if external_ip:
        return external_ip.group(0)
    else:
        raise Exception("Could not fetch IP address")


def get_domain(name=DOMAIN):
    print "Fetching Domain ID for: %s" % name
    url = "%s/domains" % APIURL

    while True:
        req = urllib2.Request(url, headers=AUTH_HEADER)
        fp = urllib2.urlopen(req)
        mybytes = fp.read()
        html = mybytes.decode("utf8")

        result = json.loads(html)

        for domain in result['domains']:
            if domain['name'] == name:
                return domain

        if 'pages' in result['links'] and 'next' in result['links']['pages']:
            url = result['links']['pages']['next']
            # Replace http to https.
            # DigitalOcean forces https request, but links are returned as http
            url = url.replace("http://", "https://")
        else:
            break

    raise Exception("Could not find domain: %s" % name)


def get_record(domain, name=RECORD):
    print "Fetching Record ID for: %s" % name
    url = "%s/domains/%s/records" % (APIURL, domain['name'])

    while True:
        req = urllib2.Request(url, headers=AUTH_HEADER)
        fp = urllib2.urlopen(req)
        mybytes = fp.read()
        html = mybytes.decode("utf8")
        result = json.loads(html)

        for record in result['domain_records']:
            if record['type'] == RTYPE and record['name'] == name:
                return record

        if 'pages' in result['links'] and 'next' in result['links']['pages']:
            url = result['links']['pages']['next']
            # Replace http to https.
            # DigitalOcean forces https request, but links are returned as http
            url = url.replace("http://", "https://")
        else:
            break

    raise Exception("Could not find record: %s" % name)


def set_record_ip(domain, record, ipaddr):
    print "Updating record %s.%s to %s" % (record['name'], domain['name'], ipaddr)

    url = "%s/domains/%s/records/%s" % (APIURL, domain['name'], record['id'])
    data = json.dumps({'data' : ipaddr}).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    headers.update(AUTH_HEADER)

    req = urllib2.Request(url, data, headers, method='PUT')
    fp = urllib2.urlopen(req)
    mybytes = fp.read()
    html = mybytes.decode("utf8")
    result = json.loads(html)

    if result['domain_record']['data'] == ipaddr:
        print ("Success")


if __name__ == '__main__':

    if RTYPE == 'A' or RTYPE == 'AAAA':
        try:
            ipaddr = get_external_ip()
            domain = get_domain()
            record = get_record(domain)
            if record['data'] == ipaddr:
                print ("Record %s.%s already set to %s." % (record['name'], domain['name'], ipaddr))
            else:
                print ("Updating ", RECORD, ".", DOMAIN, ":", datetime.now())
                set_record_ip(domain, record, ipaddr)
        except Exception as err:
            print ("Error: ", err)
    else:
        print("RTYPE should be either A or AAAA")
