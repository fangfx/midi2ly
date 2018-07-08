#!/usr/bin/env python3.5


# copied model, processing, and most variable names from midi2ly.py 
# from https://github.com/gin66/midi2ly/


import sys
sys.path.append('python_midi')
import argparse
import re
import python_midi   as midi
import matplotlib.pyplot as plt
from   lib.midipiece import *


parser = argparse.ArgumentParser(description= \
        'Read MIDI file and output some spectrograms')
parser.add_argument('-v', action='store_true', dest='verbose', help='Include verbose information in output')
parser.add_argument('midifile', help='Midifile to be processed')
args = parser.parse_args()

piece = MidiPiece(args.midifile, args.verbose)

print(piece.resolution)
for k in piece.tracks:
    plt.figure()
    plt.xlim(0, 90000)
    plt.ylim(0, 130)
    plt.title(piece.tracks[k].key)
    plt.scatter(*zip(*[(n.tick, n.pitch) for n in piece.tracks[k].notes]))
    plt.savefig(piece.tracks[k].key + ".png")
    plt.close()