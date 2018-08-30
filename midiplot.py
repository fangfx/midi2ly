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
    xmaxes = []

    for piece in xtpvd:
        x = piece[0]
        p = piece[2]
        ymax = max(ymax, max(p))
        ymin = min(ymin, min(p))
        xmaxes.append((int(max(x)) // 30 + 1) * 30) 

    ymax = (ymax // 12 + 1) * 12
    ymin = (ymin // 12) * 12
    return ymax, ymin, xmaxes

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
    plt.savefig(args.filename[:-4]+ "_duration.png")
    plt.close()
    # if shared axis looks weird, can scale the duration colors by total length
    # if do, then save a comparison of before and after length normalization to show in thesis

def compare_shared_x_y(pieces, names, xtpvd, ymax, ymin, xmax):
    # plot the comparison plots and share the x axis (time)
    figy, axesy = plt.subplots(nrows=len(pieces), ncols=1, sharey='all', figsize=(16,3.5*len(pieces)))
    figy.suptitle("Spectrograms with durations")

    figxy, axesxy = plt.subplots(nrows=len(pieces), ncols=1, sharex='all', sharey='all', figsize=(16,3.5*len(pieces)))
    figxy.suptitle("Spectrograms with durations on same time scale")

    for piece, name, xtpvd_el, axy, axxy in zip(pieces, names, xtpvd, axesy.flat, axesxy.flat):
        x = xtpvd_el[0]
        p = xtpvd_el[2]
        d = xtpvd_el[4]
        axy.grid()
        axxy.grid()
        axy.set(xlabel="Start times (s) for %s" % name, ylabel="Midi Note")
        axxy.set(xlabel="Start times (s) for %s" % name, ylabel="Midi Note")
        imy  = axy.scatter(x, p, marker='x', c=d, cmap='copper_r')
        imxy = axxy.scatter(x, p, marker='x', c=d, cmap='copper_r')
        # set the x axis for the one that changes
        maxx = int((max(x) / 30 + 1)) * 30
        if maxx < 240: # set ticks to every 30 seconds
            axy.set_xticks(range(0, maxx, 30))
        else: # set ticks to minutes if the song is long
            axy.set_xticks(range(0, maxx, 60))
        # set the x axis for the one that is shared
        if xmax < 240: # set ticks to every 30 seconds
            axxy.set_xticks(range(0, xmax, 30))
        else: # set ticks to minutes if the song is long
            axxy.set_xticks(range(0, xmax, 60))

    plt.yticks(range(ymin, ymax, 12))

    cbaxesy = figy.add_axes([0.9, 0.1, 0.02, 0.8]) # left, bottom, width, height
    cbaxesxy = figxy.add_axes([0.9, 0.1, 0.02, 0.8]) # left, bottom, width, height
    cby = figy.colorbar(imy, cax = cbaxesy)  
    cbxy = figxy.colorbar(imxy, cax = cbaxesxy)  

    cby.set_label("Duration of Note (s)")
    cbxy.set_label("Duration of Note (s)")
    figy.subplots_adjust(hspace=0.3, wspace=0.1, right=0.85)
    figxy.subplots_adjust(hspace=0.3, wspace=0.1, right=0.85)
    figy.savefig(args.filename[:-4]+ "_duration.png")
    figxy.savefig(args.filename[:-4]+ "_share_time.png")#, format='eps')
    plt.close()

def compare_and_highlight_top(pieces, names, xtpvd, ymax, ymin, num):
    # plot the comparison plots and also highlight the top 3 notes
    figSx, axesSx = plt.subplots(nrows=len(pieces), ncols=1, sharey='all', figsize=(16,3.5*len(pieces))) 
    figSx.suptitle("Spectrograms with top %d by number of occurrence" % num)

    figSd, axesSd = plt.subplots(nrows=len(pieces), ncols=1, sharey='all', figsize=(16,3.5*len(pieces))) 
    figSd.suptitle("Spectrograms with top %d by duration" % num)

    figHx, axesHx = plt.subplots(nrows=len(pieces), ncols=1, sharey='all', figsize=(16,3.5*len(pieces))) 
    figHx.suptitle("Histograms by number of occurrence")

    figHd, axesHd = plt.subplots(nrows=len(pieces), ncols=1, sharey='all', figsize=(16,3.5*len(pieces))) 
    figHd.suptitle("Histograms by duration")

    note_cts_norm = []
    note_dur_norm = []
    for piece, name, xtpvd_el, axSx, axSd, axHx, axHd in zip(pieces, names, xtpvd, axesSx, axesSd, axesHx, axesHd):
        x = xtpvd_el[0]
        p = xtpvd_el[2]
        d = xtpvd_el[4]
        notes_xp = list(map(list,zip(x,p)))
    
        # put together all the note counts across tracks in this file for each named note
        note_ct_12_totals = list(map(sum, zip(*[piece.tracks[track].note_ct_12 for track in piece.tracks])))
        total_note_ct = sum(note_ct_12_totals)
        note_cts_norm.append(list(zip(notenames, [round(n*100/total_note_ct,2) for n in note_ct_12_totals])))

        # figure out what the top 3 are
        note_occurrences = sorted(zip(note_ct_12_totals,range(12)), reverse=True)
        toptuple = note_occurrences[:num]
        top = [name for (num, name) in toptuple]
        highlight_xp = [note for note in notes_xp if note[1] % 12 in top]
        highlight_x, highlight_p = map(list,zip(*highlight_xp))

        # == plot the spectrograms and highlight the top num by occurrence
        axSx.grid()
        axSx.set(xlabel="Start times (s) for %s" % name, ylabel="Midi Note")
        imSx = axSx.scatter(x, p, marker='x', c=d, cmap='copper_r')

        #    plot the highlighted ones
        axSx.scatter(highlight_x, highlight_p, marker='o', s=10, c='b')

        #    give the plot reasonable time ticks
        xmax = int((max(x) / 30 + 1)) * 30
        if xmax < 240: # set ticks to every 30 seconds
            axSx.set_xticks(range(0, xmax, 30))
        else: # set ticks to minutes if the song is long
            axSx.set_xticks(range(0, xmax, 60))
        #    give them reasonable note ticks
        axSx.set_yticks(range(ymin, ymax, 12))

        # == plot the histogram on the histogram figure
        axHx.bar(range(12), height=[round(n*100/total_note_ct,2) for n in note_ct_12_totals], tick_label=notenames)


        # put together all the note durations across tracks in this file for each named note
        note_ct_12_d = [0]*12
        for pitch, duration in zip(p, d):
            # add the duration to the count for that pitch
            note_ct_12_d[pitch % 12] += duration
        total_note_ct_d = sum(note_ct_12_d)
        note_dur_norm.append(list(zip(notenames, [round(n*100/total_note_ct_d,2) for n in note_ct_12_d])))

        # figure out what the top 3 by duration are
        note_occurrences_d = sorted(zip(note_ct_12_d,range(12)), reverse=True)
        toptuple_d = note_occurrences_d[:num]
        top_d = [name for (num, name) in toptuple_d]
        highlight_xp_d = [note for note in notes_xp if note[1] % 12 in top_d]
        highlight_x_d, highlight_p_d = map(list,zip(*highlight_xp_d))

        # == plot the spectorgrams and highlight the top num by duration
        axSd.grid()
        axSd.set(xlabel="Start times (s) for %s" % name, ylabel="Midi Note")
        imSd = axSd.scatter(x, p, marker='x', c=d, cmap='copper_r')

        #    plot the highlighted ones
        axSd.scatter(highlight_x_d, highlight_p_d, marker='o', s=10, c='b')

        #    give the plot reasonable time ticks
        xmax = int((max(x) / 30 + 1)) * 30
        if xmax < 240: # set ticks to every 30 seconds
            axSx.set_xticks(range(0, xmax, 30))
        else: # set ticks to minutes if the song is long
            axSx.set_xticks(range(0, xmax, 60))
        #    give them reasonable note ticks
        axSx.set_yticks(range(ymin, ymax, 12))

        # == plot the histogram on the histogram figure
        axHd.bar(range(12), height=[round(n*100/total_note_ct_d,2) for n in note_ct_12_d], tick_label=notenames)
        

    # add colorbar to spectrograms and label them
    cbaxesx = figSx.add_axes([0.9, 0.1, 0.02, 0.8]) # left, bottom, width, height
    cbx = figSx.colorbar(imSx, cax = cbaxesx)  
    cbaxesd = figSd.add_axes([0.9, 0.1, 0.02, 0.8]) # left, bottom, width, height
    cbd = figSd.colorbar(imSd, cax = cbaxesd)  
    cbx.set_label("Duration of Note (s)")
    cbd.set_label("Duration of Note (s)")

    # adjust spectrograms so they're not too space inefficient
    figSx.subplots_adjust(hspace=0.3, wspace=0.1, right=0.85)
    figSd.subplots_adjust(hspace=0.3, wspace=0.1, right=0.85)

    figSx.savefig(args.filename[:-4] + "_spec_top"+ str(num) + "_by_x.png")
    figSd.savefig(args.filename[:-4] + "_spec_top"+ str(num) + "_by_d.png")
    figHx.savefig(args.filename[:-4] + "_hist_x.png")
    figHd.savefig(args.filename[:-4] + "_hist_d.png")
    plt.close(figSx)
    plt.close(figSd)
    plt.close(figHx)
    plt.close(figHd)
    return total_note_ct, note_cts_norm, note_dur_norm

def find_matches(xtpvd):
    matches = []
    for song, songname in zip(data,names):
        match = []
        for song2, song2name in zip(data,names):
            if song[0] == song2[0] and song[2] == song2[2] and songname != song2name:
                match.append(song2name)
        matches.append(match)
    return matches

data = get_x_t_p_v_d(pieces, names)
ymax, ymin, xmaxes = mins_maxes(data)
matches = find_matches(data)
treblebass = treble_bass(data, 0.8)

# compare_shared_y(pieces, names, data, ymax, ymin)
compare_shared_x_y(pieces, names, data, ymax, ymin, max(xmaxes))
# compare_and_highlight_top(pieces, names, data, ymax, ymin, 1)
totct, note_cts_norm, note_dur_norm = compare_and_highlight_top(pieces, names, data, ymax, ymin, 3)
prefix = args.filename[:-4]
fn = prefix + ".info"
f = open(fn, "w+")
for xmax, ctsdist, durdist, tb, match in zip(xmaxes, note_cts_norm, note_dur_norm, treblebass, matches):
    f.write("\"%s\"," % (prefix.split('/')[-1])) # name of the file without its extension
    f.write("\"%d\"," % len(data))               # how many files for this song
    f.write("\"%d\"," % totct)                   # total number of notes in the file
    f.write("\"%d\"," % xmax)                    # length of file in seconds rounded to next 30 second mark
    f.write("\"%.2f\"," % (totct*1.0/xmax))      # density of notes by count
    f.write("\"%s\"," % str(ctsdist))            # percentage of named notes by cts
    f.write("\"%s\"," % str(durdist))            # percentage of named notes by dur
    f.write("\"%s\"," % str(tb))                 # treble, bass, or neither
    f.write("\"%s\"," % str(match))              # files it matched in time ticks and pitch
    f.write("\n")
    # TODO: look for the histograms that are mostly zero, except 1 or 2 notes, and making note of that
f.close()


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



