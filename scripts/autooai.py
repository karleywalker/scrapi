"""
A command line utility for creating OAI harvesters for scrapi.

Creates new files in a scrapi repo that is hosted one directory up from this one.

usage: main.py [-h] [-b BASEURL] [-s SHORTNAME] [-dr DATERANGE] [-f] [-bp]

A command line interface to create and commit a new harvester

optional arguments:
  -h, --help            show this help message and exit
  -b BASEURL, --baseurl BASEURL
                        The base url for the OAI provider, everything before
                        the ?
  -s SHORTNAME, --shortname SHORTNAME
                        The shortname of the provider
  -dr DATERANGE, --daterange DATERANGE
                        date format must be isoformat YYYY-MM-DD:YYYY-MM-DD of
                        query
  -f, --favicon         flag to signal saving favicon
  -bp, --bepress        flag to signal generating bepress list

example usage: python main.py -b http://udspace.udel.edu/dspace-oai/request -s udel -f -d 30

"""

import re
import furl
import argparse
import requests
from os import listdir
from lxml import etree
from datetime import date
from datetime import timedelta
from os.path import isfile, join

URL_RE = re.compile(r'(https?:\/\/[^\/]*)')

NAMESPACES = {'dc': 'http://purl.org/dc/elements/1.1/',
              'oai_dc': 'http://www.openarchives.org/OAI/2.0/',
              'ns0': 'http://www.openarchives.org/OAI/2.0/'}

BASE_SCHEMA = ['title', 'contributor', 'creator', 'subject',
               'description', 'language', 'publisher']


def get_oai_properties(base_url, shortname, start_date, end_date):
    """ Makes a request to the provided base URL for the list of properties
        returns a dict with list of properties
    """

    try:
        prop_base = furl.furl(base_url)
        prop_base.args['verb'] = 'ListRecords'
        prop_base.args['metadataPrefix'] = 'oai_dc'

        print('requesting {}'.format(prop_base.url))
        prop_data_request = requests.get(prop_base.url)
        all_prop_content = etree.XML(prop_data_request.content)
        try:
            pre_names = all_prop_content.xpath(
                '//ns0:metadata', namespaces=NAMESPACES
            )[0].getchildren()[0].getchildren()
        except IndexError:
            raise ("There may be no records within your range, try setting date manually.")

        all_names = [name.tag.replace('{' + NAMESPACES['dc'] + '}', '') for name in pre_names]
        return list({name for name in all_names if name not in BASE_SCHEMA}) + ['setSpec']

    # If anything at all goes wrong, just render a blank form...
    except Exception as e:
        raise ValueError('OAI Processing Error - {}'.format(e))


def formatted_oai(ex_call, class_name, shortname, longname, normal_url, oai_url, prop_list, tz_gran):
    #import ipdb; ipdb.set_trace()
    unicode_longname = longname.encode('utf-8')

    return """'''
Harvester for the {0} for the SHARE project

Example API call: {1}
'''
from __future__ import unicode_literals

from scrapi.base import OAIHarvester


class {2}Harvester(OAIHarvester):
    short_name = '{3}'
    long_name = '{4}'
    url = '{5}'

    base_url = '{6}'
    property_list = {7}
    timezone_granularity = {8}
""".format(unicode_longname, ex_call, class_name, shortname, unicode_longname, normal_url, oai_url, prop_list, tz_gran)


def get_id_props(baseurl):
    identify_url = baseurl + '?verb=Identify'
    id_data_request = requests.get(identify_url)
    id_content = etree.XML(id_data_request.content)
    return id_content.xpath('//ns0:repositoryName/node()', namespaces=NAMESPACES)[0], id_content.xpath('//ns0:granularity/node()', namespaces=NAMESPACES)[0]



def parse_args():
    parser = argparse.ArgumentParser(description="A command line interface to create and commit a new harvester")

    parser.add_argument('-b', '--baseurl', dest='baseurl', type=str, help='The base url for the OAI provider, everything before the ?')
    parser.add_argument('-s', '--shortname', dest='shortname', type=str, help='The shortname of the  provider')
    parser.add_argument('-dr', '--daterange', dest='daterange', type=str, help=' date format must be isoformat YYYY-MM-DD:YYYY-MM-DD of query')

    return parser.parse_args()

def generate_oai(baseurl, shortname, start_date, end_date):
    prop_list = get_oai_properties(baseurl, shortname, start_date, end_date)
    ex_call = baseurl + '?verb=ListRecords&metadataPrefix=oai_dc'

    class_name = shortname.capitalize()

    longname, tz_gran = get_id_props(baseurl)

    found_url = URL_RE.search(baseurl).group()

    if 'hh:mm:ss' in tz_gran:
        tz_gran = True
    else:
        tz_gran = False

    return formatted_oai(ex_call, class_name, shortname, longname, found_url, baseurl, prop_list, tz_gran)


def harvester_exists(shortname):
    path = '../scrapi/scrapi/harvesters/'
    onlyfiles = [f for f in listdir(path) if isfile(join(path, f))]
    if shortname + '.py' in onlyfiles:
        return True
    else:
        return False


def main():
    args = parse_args()

    # deafault range is two days
    if not args.daterange:
        startdate = (date.today() - timedelta(2)).isoformat()
        enddate = date.today().isoformat()
    else:
        startdate, enddate = args.daterange.split(':')

    if args.baseurl:
        print args.baseurl
        text = generate_oai(args.baseurl, args.shortname, startdate, enddate)

        if harvester_exists(args.shortname):
            print('Harvester with this shortname already exists.')
            return

        with open('../scrapi/scrapi/harvesters/{}.py'.format(args.shortname), 'w') as outfile:
            outfile.write(text)

## TODO fix test generation!
## TODO add option for printng to standard out for testing
## TODO Break out test generation so on failing tests on scrapi can keep using tool


if __name__ == '__main__':
    main()
