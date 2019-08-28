#!/usr/bin/env python
#
# Copyright 2018
# Johannes K. Fichte, TU Dresden, Germany
#
# horn_bd2gr.py is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.  horn_bd2gr.py is
# distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
# License for more details.  You should have received a copy of the
# GNU General Public License along with horn_bd2gr.py.  If not, see
# <http://www.gnu.org/licenses/>.
#
import bz2
import gzip
import mimetypes
import os
import sys
from bz2 import BZ2File

import networkx as nx
from cStringIO import StringIO

__license__ = 'GPL'
__version__ = '0.0.1'

import argparse
import logging
import logging.config
from itertools import combinations
import signal

logging.config.fileConfig('logging.conf')


# noinspection PyUnusedLocal
def signal_handler(sig, frame):
    logging.warning('Received external Interrupt signal. Solvers will stop and save data')
    logging.warning('Exiting.')
    exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def is_valid_file(parser, arg):
    if not arg:
        parser.error('Missing file.')
    if not os.path.exists(arg):
        parser.error('The file "%s" does not exist!' % arg)


def parse_args():
    parser = argparse.ArgumentParser(description='%(prog)s -instance instance')
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))

    root_group = parser.add_mutually_exclusive_group()
    root_group.add_argument('-f', '--file', dest='instance', action='store', type=lambda x: os.path.realpath(x),
                            help='instance')
    args = parser.parse_args()
    is_valid_file(parser, args.instance)
    return args


def define_graph(cnf):
    logging.info('Generating Edges')
    graph = nx.Graph()
    for c in cnf.clauses:
        print c
        # GF is the graph composed by the variables of the CNF formula F
        # in which two variables v,u are adjacent iff v and u appear positively in a clause from F.
        pos_lits = filter(lambda x: x > 0, c)
        # add pairwise head
        for v, w in combinations(pos_lits, 2):
            graph.add_edge(v, w)
    # TODO: fixme num vars/edges
    return graph


try:
    import backports.lzma as xz

    xz = True
except ImportError:
    xz = False


def transparent_compression(filename):
    m_type = mimetypes.guess_type(filename)[1]
    if m_type is None:
        stream = open(filename, 'r')
    elif m_type == 'bzip2':
        stream = BZ2File(filename, 'r')
    elif m_type == 'gz' or m_type == 'gzip':
        stream = gzip.open(filename, 'r')
    elif m_type == 'xz' and xz:
        stream = xz.open(filename, 'r')
    else:
        raise IOError('Unknown input type "%s" for file "%s"' % (m_type, filename))
    return stream


class CNF(object):
    clauses = []

    def __init__(self, num_vars, num_cls):
        self.num_vars = num_vars
        self.num_cls = num_cls

    def add_clause(self, cls):
        self.clauses.append(map(lambda x: int(x), cls))


def dimacs_parse_and_gen_graph(in_stream):
    logging.info('Parsing starts...')
    try:
        num_variables = None
        num_cls = None
        cnf = None
        for line in in_stream:
            line = line.split()
            if line[0] == 'c':
                continue
            if line[0] == 'p':
                cnf = CNF(num_vars=line[2], num_cls=line[3])
                continue
            if int(line[-1]) == 0:
                cnf.add_clause(line)
                continue

        graph = define_graph(cnf)
        return graph

    except IOError:
        sys.stderr.write("Error reading from: {0}\n".format(in_stream.filename()))
        sys.stderr.flush()
        raise IOError


def add_mapping(mapping, key, idx):
    try:
        return (idx, mapping[key])
    except KeyError:
        mapping[key] = idx
        return (idx + 1, idx)


def write_graph(ostream, graph):
    mapping = {}
    idx = 1
    ostream.write("p td %s %s\n" % (graph.number_of_nodes(), graph.number_of_edges()))
    for edge in graph.edges():
        assert (edge[0] != edge[1])
        idx, v1 = add_mapping(mapping, edge[0], idx)
        idx, v2 = add_mapping(mapping, edge[1], idx)
        ostream.write("%s %s\n" % (v1, v2))
    ostream.flush()


if __name__ == '__main__':
    args = parse_args()
    instance = args.instance
    output_instance = "%s.gr.bz2" % instance

    # unpack the file if required
    input_stream = transparent_compression(instance)

    # read the dimacs file
    graph = dimacs_parse_and_gen_graph(input_stream)

    ostream = StringIO()
    write_graph(ostream=ostream, graph=graph)
    tarbz2contents = bz2.compress(ostream.getvalue(), 9)

    with open(output_instance, 'wb') as fh:
        fh.write(tarbz2contents)
    exit(0)
