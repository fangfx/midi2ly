#!/usr/bin/env python3.5

# copied model, processing, and most variable names from midi2ly.py 
# from https://github.com/gin66/midi2ly/
# and changed whatever I needed for my spectrograms
# please see original for difference

import sys
sys.path.append('python_midi')
import argparse
import re
import python_midi   as midi
import lib.lilypond  as lilypond
import lib.key_guess as key_guess
from   lib.miditrack import *

parser = argparse.ArgumentParser(description= \
        'Read MIDI file and output some spectrograms')
parser.add_argument('-t', nargs=1, dest='title',    help='Title of the song')
parser.add_argument('-c', nargs=1, dest='composer', help='Composer of the song')
parser.add_argument('-v', action='store_true', dest='verbose', help='Include verbose information in output')
parser.add_argument('midifile', help='Midifile to be processed')
args = parser.parse_args()

midifile = args.midifile
try:
    pattern = midi.read_midifile(midifile)
except TypeError as e:
    print('Cannot read "%s" as midifile' % args.midifile)
    print('Exception says: %s' % e)
    sys.exit(2)

MidiTrack.resolution = pattern.resolution
for p in pattern:
    mt = MidiTrack(p,args.verbose)

if args.list:
    for mt in MidiTrack.tracklist:
        print(mt.index,':',mt)
    sys.exit(0)

for mt in MidiTrack.tracklist:
    n = '%d' % mt.index
    if n in args.drum_list:
        mt.output        = True
        mt.output_drums  = True
    if n in args.voice_list:
        mt.output        = True
        mt.output_voice  = True
    if n in args.piano_list:
        mt.output        = True
        mt.output_piano  = True
    if n in args.lyrics_list:
        mt.output        = True
        mt.output_lyrics = True
    mt.trim_notes()
    mt.trim_lyrics()
    mt.split_same_time_notes_to_same_length()

MidiTrack.fill_bars()
print('%% ',MidiTrack.bars)
print('%% ',len(MidiTrack.bars))
for mt in MidiTrack.tracklist:
    mt.split_notes_at_bar()

key_tracks = [ mt for mt in MidiTrack.tracklist if mt.output_piano or mt.output_voice]
# Tuples with (starttick,endtick,key,stats)
key_list = key_guess.calculate(key_tracks)
print('%% KEYS: ',key_list)

if False:
    del_silence = True
    while del_silence:
        for k in all_lily:
            if bars[k][0] != 'r1':
                del_silence = False
                break
        if del_silence:
            for k in all_lily:
                bars[k].pop(0)


# RECREATE in lilypond format
print('\\version "2.18.2"')
print('\\header {')
print('  title = "%s"' % title)
print('  composer = "%s"' % composer)
print('}')

lpiano_voices = []
rpiano_voices = []
drum_voices   = []
song_voices   = []
lyric_voices  = []
for mt in MidiTrack.tracklist:
    if mt.output:
        mode = ''
        key = 'Track%c' % (64+mt.index)
        fmt = None
        if mt.output_drums:
            drum_voices.append(key)
            bars = mt.bar_lily_notes
            mode = '\\drummode'
            fmt = 'fmt_drum'
        if mt.output_piano:
            if mt.advise_treble():
                rpiano_voices.append(key)
            else:
                lpiano_voices.append(key)
            bars = mt.bar_lily_notes
            fmt = 'fmt_voice'
        if mt.output_voice:
            song_voices.append(key)
            bars = mt.bar_lily_notes
            fmt = 'fmt_voice'
        if fmt is not None:
            print(key,'= ' + mode + '{')
            for deco,bar in zip(bar_deco,bars):
                deco['bar'] = bar
                print(deco[fmt] % deco)
            print('}')
for mt in MidiTrack.tracklist:
    if mt.output:
        if mt.output_lyrics:
            mode = ''
            for bars,cnt in zip(mt.bar_lily_words,'ABCDEFGHIJKLM'):
                key = mt.key + '_Lyric_' + cnt
                lyric_voices.append(key)
                mode = '\\lyricmode'
                fmt = 'fmt_lyric'
                print(key,'= ' + mode + '{')
                for deco,bar in zip(bar_deco,bars):
                    deco['bar'] = bar
                    print(deco[fmt] % deco)
                print('}')

print('%% Piano links =',lpiano_voices)
print('%% Piano rechts=',rpiano_voices)
print('%% Drum=' ,drum_voices)
print('%% Song=' ,song_voices)

pianostaff = ''
drumstaff  = ''
songstaff  = ''
lyricstaff = ''

key = '\\key c \\major'
if len(lpiano_voices) > 0 or len(rpiano_voices) > 0:
    pianostaff  = '\\new PianoStaff << \\context Staff = "1" << '
    pianostaff += '\\set PianoStaff.instrumentName = #"Piano"'
    for v,x in zip(rpiano_voices,['One','Two','Three','Four']):
        pianostaff += '\\context Voice = "RPiano%s" { \\voice%s \\clef "treble" \\%s }' % (x,x,v)
    pianostaff += '>> \\context Staff = "2" <<'
    for v,x in zip(lpiano_voices,['One','Two','Three','Four']):
        pianostaff += '\\context Voice = "LPiano%s" { \\voice%s \\clef "bass" \\%s }' % (x,x,v)
    pianostaff += ' >> >>'

if len(drum_voices) > 0:
    drumstaff  = '\\new DrumStaff <<'
    for v,x in zip(drum_voices,['One','Two','Three','Four']):
        drumstaff += '\\new DrumVoice {\\voice%s \\clef "percussion" \\%s }' % (x,v)
    drumstaff += ' >>'

if len(song_voices) > 0:
    songstaff  = '\\new Staff <<'
    for v,x in zip(song_voices,['One','Two','Three','Four']):
        songstaff += '\\new Voice {\\voice%s \\clef "treble" \\%s }' % (x,v)
    songstaff += ' >>'

if len(lyric_voices) > 0:
    for v in lyric_voices:
        lyricstaff += '\\new Lyrics \\' + v

print("""
% The score definition
\\book {
  \\score {
    <<
            \\set Score.alternativeNumberingStyle = #'numbers-with-letters
""")
#for v,x in zip(song_voices,['One','Two','Three','Four']):
#    print('\\new Voice = "melody%s" { \\voice%s \\clef "bass" \\key %s %s \\%s}' % (x,x,key,time_sig,v))
print(songstaff)
print(lyricstaff)
print(pianostaff)
print(drumstaff)
print("""
    >>
    \\layout {}
  }
    \\header {
        tagline = "%s"
    }
}
""" % title)

print("""
% The score definition
\\score {
    \\unfoldRepeats
    <<
""")
print(songstaff)
print(pianostaff)
print(drumstaff)
print("""
    >>
    \\midi {
            \\tempo 4 = 127
    }
}
""")

