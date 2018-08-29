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
from   lib.key_guess import notes as notenames

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
            # print("importing from " + names[i])
            pieces.append(MidiPiece(names[i], args.verbose))
else:
    if os.path.isfile(args.filename):
        pieces.append(MidiPiece(args.filename, args.verbose))

# print(pieces[0].resolution)
colors = ["r", "b", "g"]

def get_x_t_p_v_d(p, n):
    xtpvd = []

    for piece, name in zip(p, n):
        # find the seconds, ticks, pitches, velocities, durations and make separate lists for each
        s_tick_pitch_vel_dur = [[float(n.us)/1000000, n.tick, n.pitch, n.velocity, float(n.duration_us)/1000000] for track in piece.tracks for n in piece.tracks[track].notes]
        el = list(map(list,zip(*s_tick_pitch_vel_dur)))
        xtpvd.append(el)
    return xtpvd

def mins_maxes(xtpvd):
    ymax = 60
    ymin = 60
    xmax = 0

    for piece in xtpvd:
        x = piece[0]
        p = piece[2]
        ymax = max(ymax, max(p))
        ymin = min(ymin, min(p))
        xmax = max(xmax, max(x))

    ymax = (ymax // 12 + 1) * 12
    ymin = (ymin // 12) * 12
    xmax = (int(max(x)) // 30 + 1) * 30
    return ymax, ymin, xmax

def treble_bass(xtpvd, threshold):
    tb = []
    for piece in xtpvd:
        p = piece[2]
        num_above = sum(i > 60 for i in p)
        num_below = sum(i < 60 for i in p)
        istb = "both ranges"
        if float(num_above) / len(p) > threshold:
            istb = "treble only"
        elif float(num_below) / len(p) > threshold:
            istb = "bass only"
        tb.append(istb)
    return tb

def compare_shared_y(pieces, names, xtpvd, ymax, ymin):
    # plot comparison plots and share the y axis (notes)
    plt.figure()
    fig, axes = plt.subplots(nrows=len(pieces), ncols=1, sharey='all', figsize=(16,3.5*len(pieces)))

    for piece, name, xtpvd_el, ax in zip(pieces, names, xtpvd, axes.flat):
        x = xtpvd_el[0]
        p = xtpvd_el[2]
        d = xtpvd_el[4]
        ax.grid()
        ax.set(xlabel="Start times (s) for %s" % name, ylabel="Midi Note")
        im = ax.scatter(x, p, marker='x', c=d, cmap='copper_r')
        xmax = int((max(x) / 30 + 1)) * 30
        if xmax < 240: # set ticks to every 30 seconds
            ax.set_xticks(range(0, xmax, 30))
        else: # set ticks to minutes if the song is long
            ax.set_xticks(range(0, xmax, 60))

    plt.yticks(range(ymin, ymax, 12))
    cbaxes = fig.add_axes([0.9, 0.1, 0.02, 0.8]) # left, bottom, width, height
    cb = plt.colorbar(im, cax = cbaxes)  

    cb.set_label("Duration of Note (s)")
    plt.subplots_adjust(hspace=0.3, wspace=0.1, right=0.85)
    plt.savefig(args.filename[:-4]+ ".png")
    plt.close()
    # if shared axis looks weird, can scale the duration colors by total length
    # if do, then save a comparison of before and after length normalization to show in thesis

def compare_shared_x_y(pieces, names, xtpvd, ymax, ymin, xmax):
    # plot the comparison plots and share the x axis (time)
    plt.figure()
    fig, axes = plt.subplots(nrows=len(pieces), ncols=1, sharex='all', sharey='all', figsize=(16,3.5*len(pieces)))

    for piece, name, xtpvd_el, ax in zip(pieces, names, xtpvd, axes.flat):
        x = xtpvd_el[0]
        p = xtpvd_el[2]
        d = xtpvd_el[4]
        ax.grid()
        ax.set(xlabel="Start times (s) for %s" % name, ylabel="Midi Note")
        im = ax.scatter(x, p, marker='x', c=d, cmap='copper_r')

    plt.yticks(range(ymin, ymax, 12))
    if xmax < 240: # set ticks to every 30 seconds
        plt.xticks(range(0, xmax, 30))
    else: # set ticks to minutes if the song is long
        plt.xticks(range(0, xmax, 60))

    cbaxes = fig.add_axes([0.9, 0.1, 0.02, 0.8]) # left, bottom, width, height
    cb = plt.colorbar(im, cax = cbaxes)  

    cb.set_label("Duration of Note (s)")
    plt.subplots_adjust(hspace=0.3, wspace=0.1, right=0.85)
    plt.savefig(args.filename[:-4]+ "_share_time.png")#, format='eps')
    plt.close()

def compare_and_highlight_top(pieces, names, xtpvd, ymax, ymin, num):
    # plot the comparison plots and also highlight the top 3 notes
    # plt.figure()
    fig, axes = plt.subplots(nrows=len(pieces), ncols=1, sharey='all', figsize=(16,3.5*len(pieces)))

    note_cts = []
    for piece, name, xtpvd_el, ax in zip(pieces, names, xtpvd, axes.flat):
        x = xtpvd_el[0]
        p = xtpvd_el[2]
        d = xtpvd_el[4]
    
        # create subplots and display them
        ax.grid()
        ax.set(xlabel="Start times (s) for %s" % name, ylabel="Midi Note")
        # plt.ylim(20,100)
        # im = ax.scatter(x, p, marker='x', c=d, cmap='copper_r')
        # figure out what the top 3 are
        note_ct_12_totals = list(map(sum, zip(*[piece.tracks[track].note_ct_12 for track in piece.tracks])))
        total_notes = sum(note_ct_12_totals)
        note_cts.append(list(zip(notenames, [round(n*100/total_notes,2) for n in note_ct_12_totals])))
        note_occurrences = sorted(zip(note_ct_12_totals,range(12)), reverse=True)
        toptuple = note_occurrences[:num]
        top = [name for (num, name) in toptuple]
        # thingymajig = str([notenames[note] for note in top])
        notes = list(map(list,zip(*xtpvd_el)))
        highlight_xtpvd = [note for note in notes if note[2] % 12 in top]
        highlight_x, _, highlight_p, _, _ = map(list,zip(*highlight_xtpvd))
        # ax.scatter(highlight_x, highlight_p, marker='o', s=10, c='b')
        xmax = int((max(x) / 30 + 1)) * 30
        if xmax < 240: # set ticks to every 30 seconds
            ax.set_xticks(range(0, xmax, 30))
        else: # set ticks to minutes if the song is long
            ax.set_xticks(range(0, xmax, 60))

        # figure out what the top 3 are by duration
        note_ct_12_d = [0]*12
        for pitch, duration in zip(p, d):
            # add the duration to the pitch
            note_ct_12_d[pitch % 12] += duration
        total_notes = sum(note_ct_12_d)
        toptuple_d = sorted(zip(note_ct_12_totals,range(12)), reverse=True)[:num]
        top_d = [name for (num, name) in toptuple]
        notes = list(map(list,zip(*xtpvd_el)))
        highlight_xtpvd = [note for note in notes if note[2] % 12 in top_d]
        highlight_x, _, highlight_p, _, _ = map(list,zip(*highlight_xtpvd))
        # ax.scatter(highlight_x, highlight_p, marker='o', s=10, c='b')
        thingymajig_d = str([notenames[note] for note in top])
        im = ax.bar(range(12), height=[round(n*100/total_notes,2) for n in note_ct_12_d], tick_label=notenames)
        # print(thingymajig_d)
        
    # plt.yticks(range(ymin, ymax, 12))
    # cbaxes = fig.add_axes([0.9, 0.1, 0.02, 0.8]) # left, bottom, width, height
    # cb = plt.colorbar(im, cax = cbaxes)  

    # cb.set_label("Duration of Note (s)")
    # plt.subplots_adjust(hspace=0.3, wspace=0.1, right=0.85)
    fig.savefig(args.filename[:-4]+ "_hist_d"+ str(num) + ".png")#, format='eps')
    plt.close(fig)
    return note_cts

def find_matches(xtpvd):
    matches = []
    for song in data:
        match = []
        for song2, song2name in zip(data,names):
            if song[0] == song2[0] and song[2] == song2[2]:
                match.append(song2name)
        matches.append(match)
    return matches

data = get_x_t_p_v_d(pieces, names)
ymax, ymin, xmax = mins_maxes(data)
matches = find_matches(data)

compare_shared_y(pieces, names, data, ymax, ymin)
compare_shared_x_y(pieces, names, data, ymax, ymin, xmax)
# compare_and_highlight_top(pieces, names, data, ymax, ymin, 1)
note_cts = compare_and_highlight_top(pieces, names, data, ymax, ymin, 3)
prefix = args.filename[:-4]
fn = prefix + ".info"
f = open(fn, "w+")
for cts, tb in zip(note_cts, treble_bass(data, 0.8)):
    totct = sum([b for (a,b) in cts])
    f.write("\"%s\"," % (prefix.split('/')[-1]))
    f.write("\"%d\"," % len(note_cts))
    f.write("\"%d\"," % totct)
    f.write("\"%d\"," % xmax)
    f.write("\"%.2f\"," % (totct*1.0/xmax))
    f.write("\"%s\"," % str(cts)) # show percentages instead of numbers
    f.write("\"%s\"," % str(tb))
    f.write("\n")
f.close()
print(notenames)


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



