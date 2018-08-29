# copied model, processing, and most variable names from miditrack.py 
# from https://github.com/gin66/midi2ly/

import python_midi as midi
from pprint import pprint

# start here with model for a midi file
# a MidiPiece contains MidiTracks, which contain MidiNotes
# Any other messages are interpreted with musical meaning in mind,
# so tempo info will calculate the clock-time marks for things

class MidiNote(object):
    """docstring for MidiNote"""
    def __init__(self, index, track, pitch, velocity, tick, duration_t, extended=False):
        super(MidiNote, self).__init__()
        self.index       = index
        self.track       = track
        self.pitch       = pitch
        self.velocity    = velocity
        self.note        = midi.constants.NOTE_VALUE_MAP_FLAT[pitch]
        self.duration    = duration_t
        self.tick        = tick
        self.us          = 0            # microseconds
        self.duration_t  = duration_t
        self.duration_us = 0            # microseconds
        self.extended    = extended

    # add a function to change us and duration_us
    def set_us(self, tick2us):
        self.us          = tick2us(self.tick)
        self.duration_us = tick2us(self.duration_t)

class MidiTrack(object):
    """docstring for MidiTrack"""
    def __init__(self, index, pattern, verbose):
        super(MidiTrack, self).__init__()
        self.index          = index
        self.key            = None
        self.trackname      = None
        self.instrument     = None
        self.ticks_set      = set()
        self.time_signature = {}
        self.notes          = []
        self.note_ct_128    = [0]*128
        self.note_ct_12     = [0]*12
        self.tempos         = dict()

        for e in pattern:
            if type(e) is midi.events.TrackNameEvent:
                self.trackname = e.text
                break

        for e in pattern:
            if type(e) is midi.events.InstrumentNameEvent:
                self.instrument = e.text
                break

        self.key = '%s_%s' % (self.trackname, self.instrument)
        self.key = self.key.replace(' ','_')
        
        pattern.make_ticks_abs()

        for e in pattern:
            if type(e) is midi.events.TimeSignatureEvent:
                s = '\\numericTimeSignature\\time %d/%d' \
                            % (e.numerator,e.denominator)
                self.time_signature[e.tick] = s
            if type(e) is midi.events.NoteOnEvent and e.velocity > 0:
                self.ticks_set.add(e.tick)
            if type(e) is midi.events.SetTempoEvent:
                # print("Found tempo change at tick %d to %d microseconds per quarter note" % (e.tick, e.mpqn))
                self.tempos[e.tick] = e.mpqn

        transient = {}
        note_i = 0
        for e in pattern:
            if verbose:
                print('%% Event: ',e)

            if type(e) is midi.events.NoteOnEvent and e.velocity > 0:
                if e.pitch in transient:
                    transient[e.pitch].append(e)
                else:
                    transient[e.pitch] = [e]

                self.note_ct_128[e.pitch     ] += 1
                self.note_ct_12 [e.pitch % 12] += 1

            if type(e) is midi.events.NoteOnEvent and e.velocity == 0 \
                    or type(e) is midi.events.NoteOffEvent:
                if e.pitch not in transient:
                    print('%% NoteOff without NoteOn: ',e)
                else:
                    se = transient[e.pitch].pop(0)
                    if len(transient[e.pitch]) == 0:
                        del transient[e.pitch]

                    note = MidiNote(note_i,self,se.pitch,se.velocity,se.tick,e.tick-se.tick)
                    self.notes.append(note)
                    note_i += 1
                    if verbose:
                        print('%% => ',note)
        if len(transient) > 0:
            raise Exception('MIDI-File damaged: Stuck Notes detected')

        self.notes = self.sort_notes(self.notes)

    def sort_notes(self,notes):
        return sorted(notes,key=lambda n:n.tick+n.pitch/1000)

class MidiPiece(object):
    """docstring for MidiPiece"""
    def __init__(self, midi_fn, verbose):
        super(MidiPiece, self).__init__()
        self.midi_fn    = midi_fn
        self.tempos     = dict()
        self.tempo2us   = dict()
        self.tracks     = {}
        self.ticks_s    = set()
        self.ticks_l    = []

        # read the file into the pattern and get the resolution
        try:
            pattern = midi.read_midifile(midi_fn)
        except TypeError as e:
            print('Cannot read "%s" as midifile' % midi_fn)
            print('Exception says: %s' % e)
            sys.exit(2)
        self.resolution = pattern.resolution
        
        # read each track of the pattern and try to get all the notes and tempos
        index = 0
        for p in pattern:
            track = MidiTrack(index, p, verbose)
            if (track.key not in self.tracks) and track.notes:
                # print("Found %d notes in track %d" % (len(track.notes), index))
                # put all ticks into ticks set
                self.ticks_s = self.ticks_s | track.ticks_set
                # put track into tracks set
                self.tracks[track.key] = track
            elif (track.key not in self.tracks) and track.tempos:
                # print("Found %d tempos in track %d" % (len(track.tempos), index))
                self.tempos.update(track.tempos)
            # else:
            #     print("No notes found in track %d" % index)
            index += 1
        self.ticks_l = sorted(list(self.ticks_s))
        
        # populate the tempo conversion dictionary
        if self.tempos:
            tempoticks = sorted(list(self.tempos.keys()))
            tempoticks.append(self.ticks_l[-1])
            
            # up to the tick, add microseconds together
            us_ct = 0
            pr_tick = tempoticks[0]
            for i in range(1, len(tempoticks)):
                tick = tempoticks[i]
                self.tempo2us[pr_tick] = us_ct
                us_ct += (tick - pr_tick)*self.tempos[pr_tick]
                pr_tick = tick

        # convert all notes to microseconds
        for t in self.tracks:
            # print("Track %s" % t)
            # print("at tick %d is " % self.tracks[t].notes[200].tick)
            # print(self.tick2us(self.tracks[t].notes[200].tick))
            for n in self.tracks[t].notes:
                n.set_us(self.tick2us)

    def tick2us(self, tick):
        default_MIDI_tempo = 500000
        tempoticks = sorted([t for t in self.tempos.keys() if t < tick])
        last = 0
        if tempoticks:
            last = tempoticks[-1]    
            return (self.tempo2us[last] + (tick - last)*self.tempos[last])/float(self.resolution)
        return tick*default_MIDI_tempo/float(self.resolution)
