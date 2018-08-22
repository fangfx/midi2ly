#!/usr/bin/env python3.5


# copied model, processing, and most variable names from midi2ly.py 
# from https://github.com/gin66/midi2ly/


import sys, os
sys.path.append('python_midi')
import argparse
import re
import numpy as np
import python_midi   as midi
import matplotlib
import matplotlib.pyplot as plt
from   lib.midipiece import *

font = {'family' : 'normal',
        'weight' : 'bold',
        'size'   : 18}

matplotlib.rc('font', **font)


parser = argparse.ArgumentParser(description= \
        'Read MIDI file and output some spectrograms')
parser.add_argument('-v', action='store_true', dest='verbose', help='Include verbose information in output')
parser.add_argument('-d', action='store_true', dest='duplicates', help='Argument is text file containing filenames')
parser.add_argument('filename', help='File to be processed')
args = parser.parse_args()

pieces = []
names  = []
if args.duplicates:
    if os.path.isfile(args.filename):
        with open(args.filename) as f:
            for line in f:
                names.append(line.strip())
        for i in range(len(names)):
            print("importing from " + names[i])
            pieces.append(MidiPiece(names[i], args.verbose))
else:
    if os.path.isfile(args.filename):
        pieces.append(MidiPiece(args.filename, args.verbose))

print(pieces[0].resolution)
# print(pieces[0].tempos[0])
colors = ["r", "b", "g"]

plt.figure()
fig, axes = plt.subplots(nrows=len(pieces), ncols=1, sharey='all', figsize=(16,3.5*len(pieces)))
ct = 0
for piece, name, ax in zip(pieces, names, axes.flat):
    # find the seconds, ticks, pitches, velocities, durations and make separate lists for each
    s_tick_pitch_vel_dur = [[float(n.us)/1000000, n.tick, n.pitch, n.velocity, float(n.duration_us)/1000000] for track in piece.tracks for n in piece.tracks[track].notes]
    x, t, p, v, d = map(list,zip(*s_tick_pitch_vel_dur))

    # create subplots and display them
    ax.grid()
    ax.set(xlabel="Start times (s) for %s" % name, ylabel="Midi Note")
    # plt.ylim(20,100)
    im = ax.scatter(x, p, marker='x', c=d, cmap='copper_r')

cbaxes = fig.add_axes([0.9, 0.1, 0.02, 0.8]) # left, bottom, width, height
cb = plt.colorbar(im, cax = cbaxes)  

cb.set_label("Duration of Note (s)")
plt.subplots_adjust(hspace=0.3, wspace=0.1, right=0.85)
plt.savefig(args.filename[:-4]+ ".png")#, format='eps')
plt.close()
# https://matplotlib.org/examples/pylab_examples/shared_axis_demo.html
# if shared axis looks weird, can scale the duration colors by total length
# if do, then save a comparison of before and after length normalization to show in thesis


# =============================================================================================================
# =======================================    plot notes against time, in microseconds and in ticks
# plt.figure(figsize=(16, 9))

# plt.subplot(211)
# plt.grid()
# plt.title("Plot of %s Comparing Seconds vs Ticks" % args.filename)
# plt.xlabel("Seconds")
# plt.ylabel("Midi Note")
# plt.scatter(x, p, marker='.', color="b")

# plt.subplot(212)
# plt.grid()
# plt.xlabel("Ticks")
# plt.ylabel("Midi Note")
# plt.scatter(t, p, marker='.', color="r")

# plt.tight_layout()
# plt.savefig(args.filename[:-4] + ".png")
# plt.close()

# # =======================================    plot the velocities and durations
# plt.figure(figsize=(16,9))

# plt.subplot(211)
# plt.grid()
# plt.title("Plot of %s Comparing Velocity and Duration" % args.filename)
# plt.ylabel("Midi Note")
# plt.ylim(20,100)
# plt.scatter(x, p, marker='x', c=v, cmap='summer_r')
# cb = plt.colorbar(pad=0.01)
# cb.set_label("Velocities")

# plt.subplot(212)
# plt.grid()
# plt.xlabel("Start times (s)")
# plt.ylabel("Midi Note")
# plt.ylim(20,100)
# plt.scatter(x, p, marker='x', c=d, cmap='copper_r')
# cb = plt.colorbar(pad=0.01)
# cb.set_label("Durations")

# plt.tight_layout()
# # plt.show()
# plt.savefig(args.filename[:-4] + "_velocities_durations.png")
# plt.close()

# ============== histogram of named notes

# plt.figure(figsize=(16,9))
# named = [0]*12
# for track in pieces[0].tracks:
#     if track.notes:
#         plt.bar(ttrack.note_ct_12,)

# =======================================    plot??
# for window in [1,2,3,5,10]:
# # window = 10 # second, before and after
#     vdiffs = []
#     ddiffs = []
#     for note in range(len(x)):
#         indices = [] # get all the indices of times that are within window of this note
#         for index in range(len(x)):
#             if np.absolute(x[index] - x[note]) < window:
#                 indices.append(index)
#         velocities = [v[i] for i in indices]
#         durations  = [d[i] for i in indices]
#         av_v = np.average(velocities)
#         av_d = np.average(durations)
#         vdiff = v[note] - av_v
#         ddiff = d[note] - av_d
#         vdiffs.append(vdiff)
#         ddiffs.append(ddiff)

#     plt.figure(figsize=(16,9))

#     plt.subplot(211)
#     plt.grid()
#     plt.title("Plot of %s minus average of all notes within %d of start time" % (args.filename, window))
#     plt.ylabel("Midi Note")
#     plt.scatter(x, p, marker='x', c=vdiffs, cmap='summer_r')
#     cb = plt.colorbar(pad=0.01)
#     cb.set_label("Velocity difference")

#     plt.subplot(212)
#     plt.grid()
#     plt.xlabel("Start times (s)")
#     plt.ylabel("Midi Note")
#     plt.scatter(x, p, marker='x', c=ddiffs, cmap='copper_r')
#     cb = plt.colorbar(pad=0.01)
#     cb.set_label("Duration difference")

#     plt.tight_layout()
#     plt.savefig("%s_v_d_%ddiffs.png" %(args.filename[:-4], window))
#     plt.close()



