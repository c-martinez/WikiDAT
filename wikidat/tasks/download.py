# -*- coding: utf-8 -*-
"""
Created on Thu Apr 10 18:02:16 2014

Download manager for dump files

@author: jfelipe
"""
from bs4 import BeautifulSoup
import multiprocessing as mp
import itertools
import urllib2
import requests
import re
import os
import hashlib


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class DumpIntegrityError(Error):
    """Exception raised for errors in the input.

    Attributes:
        msg  -- explanation of the error
    """

    def __init__(self, msg):
        self.msg = msg


class Downloader(object):
    """
    Download manager for any type of Wikipedia dump file
    Subclasses will instantiate methods to deal with the specific tasks
    to download each type of dump file
    """
    pass


class RevDownloader(object):
    """
    Downloads revision dump files from http://dumps.wikimedia.org
    There are different instances of revision dumps (metadata only, complete
    history, etc.) which are managed by its subclasses
    """

    def __init__(self, mirror="http://dumps.wikimedia.org/",
                 language='scowiki'):
        self.language = language
        self.mirror = mirror
        self.base_url = "".join([self.mirror, self.language])
        html_dates = requests.get(self.base_url)
        soup_dates = BeautifulSoup(html_dates.text)

        # Get hyperlinks and timestamps of dumps for each available date
        # Ignore first line with link to parent folder
        self.dump_urldate = [link.get('href')
                             for link in soup_dates.find_all('a')][1:]
        self.dump_dates = [link.text
                           for link in soup_dates.find_all('td', 'm')][1:]
        self.match_pattern = ""  # Store re in subclass for type of dump file
        self.dump_basedir = language + "_dumps"
        self.dump_paths = []  # List of paths to dumps in local filesystem
        self.md5_codes = {}  # Dict for md5 codes to verify dump files

    def download(self, dump_date=None):
        """
        Download all dump files for a given language in their own folder
        Return list of paths to dump files to be processed

        Default target dump_date is latest available dump (index -2, as the
        last item is the generic 'latest' date, not a real date)
        """
        if dump_date is None:
            dump_date = self.dump_dates[-2]
        # Obtain content for dump summary page on requested date
        target_url = "".join([self.base_url, "/", dump_date])
        html_dumps = requests.get(target_url)
        soup_dumps = BeautifulSoup(html_dumps.text)

        # First of all, check that status of dump files is Done (ready)
        status_dumps = soup_dumps.find('p', class_='status').span.text
        if status_dumps != 'Dump complete':
            # TODO: Raise error if dump is not ready on requested date
            # Think about offering an alternative to the user (latest dump)
            pass

        # Dump file(s) ready, proceed with list of files and download
        self.dump_urls = [link.get('href') for link in (soup_dumps.
                          find_all(href=re.compile(self.match_pattern)))]

        # Create directory for dump files if needed
        self.dump_dir = os.path.join(self.dump_basedir, dump_date)
        if not os.path.exists(self.dump_dir):
            os.makedirs(self.dump_dir)

        for url1, url2 in itertools.izip_longest(self.dump_urls[::2],
                                                 self.dump_urls[1::2],
                                                 fillvalue=None):
            # Due to bandwith limitations in WMF mirror servers, you will not
            # be allowed to download more than 2 dump files at the same time
            proc_get1 = mp.Process(target=self._get_file,
                                   args=(dump_url, self.dump_dir,))
            proc_get1.start()
            # Control here for even number of dumps (last element is None)
            if url2 is not None:
                proc_get2 = mp.Process(target=self._get_file,
                                       args=(dump_url, self.dump_dir,))
                proc_get2.start()
                proc_get2.join()

            # Wait until all downloads are finished
            proc_get1.join()

        # Verify integrity of downloaded dumps
        try:
            self._verify(dump_date)
            # TODO: Raise an exception when integrity problems are detected
        except IntegrityException as e:
            print "File integrity error({0}): {1}".format(e.errno, e.strerror)

        # Return list of paths to dumpfiles for data extraction
        return self.dump_paths, dump_date

    def _get_file(self, dump_url, dump_dir):
        """
        Retrieve individual dump file from dump_url and save it in dump_dir
        """
        file_name = dump_url.split('/')[-1]
        dump_file = urllib2.urlopen(base_url + dump_url)
        path_file = os.path.join(dump_dir, file_name)
        store_file = open(os.path.join(dump_dir, file_name), 'wb')
        file_meta = dump_file.info()
        file_size = int(file_meta.getheaders("Content-Length")[0])
        print "Downloading: %s Bytes: %s" % (file_name, file_size)
        store_file.write(dump_file.read())
        store_file.close()
        self.dump_paths.append(path_file)

    def _verify(self, dump_date):
        """
        Verify integrity of downloaded dump files against MD5 checksums
        """
        html_dumps = requests.get("".join([self.target_url, "/",
                                           dump_date]))
        soup_dumps = BeautifulSoup(html_dumps.text)
        md5_url = soup_dumps.find('p', class_='checksum').a['href']
        md5_codes = requests.get("".join([self.mirror, md5_url])).text
        md5_codes = md5_codes.split('\n')

        for fileitem in md5_codes:
            f = item.split()
            if len(f) > 0:
                self.md5_codes[f[1]] = f[0]  # dict[fname] = md5code

        for path in self.dump_paths:
            filename = path.split()[1]  # Get filename from path
            file_md5 = hashlib.md5(open(path).read()).hexdigest()
            original_md5 = self.md5_codes[filename]
            # TODO: Compare md5 hash of retrieved file with original
            if file_md5 != original_md5:
                # Raise error if they do not match
                raise DumpIntegrityError('Dump file integrity error detected!')


class RevHistDownloader(RevDownloader):
    """
    Downloads revision history files from http://dumps.wikimedia.org
    These are files with complete revision history information (all text)
    """

    def __init__(self, mirror, language):
        super(RevHistDownloader, self).__init__(mirror=mirror,
                                                language=language)
        # Customized pattern to find dump files on mirror server page
        self.match_pattern = 'pages-meta-history[\S]*\.xml\.7z'


class RevMetaDownloader(RevDownloader):
    """
    Downloads revision meta files from http://dumps.wikimedia.org
    These are files with complete metadata for every revision (including
    rev_len, as stored in Wikipedia DB) but no revision text
    """

    def __init__(self, mirror, language):
        super(RevMetaDownloader, self).__init__(mirror=mirror,
                                                language=language)
# Customized pattern to find dump files on mirror server page
        self.match_pattern = 'stub-meta-history[\d]+\.xml\.gz'


class LoggingDownloader(Downloader):
    """
    Download logging dump files
    """
    pass


class SQLDumpDownloader(Downloader):
    """
    Download compressed or uncompressed sql dump files ready to be directly
    loaded to the local database
    """
    pass
    