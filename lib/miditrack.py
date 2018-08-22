import python_midi   as midi

class MidiNote(object):
    count = 0

    def __init__(self,track,pitch,velocity,at_tick,duration,extended=False):
        MidiNote.count += 1
        self.index    = MidiNote.count
        self.note     = midi.constants.NOTE_VALUE_MAP_FLAT[pitch]
        self.track    = track
        self.pitch    = pitch
        self.velocity = velocity
        self.at_tick  = at_tick
        self.duration = duration
        self.extended = extended      # is True, if has following note

    def __str__(self):
        return 'Note(%d %s:%d,%d,%d ticks,%s) in %r at %d' \
                % (self.index,self.note,self.pitch,self.velocity,\
                   self.duration, '~' if self.extended else '|', \
                   self.track,self.at_tick)

    __repr__ = __str__

class MidiTrack(object):
    tracklist      = []
    tracks         = {}
    ticks_set      = set()
    ticks          = []
    bars           = []     # List of tuples (start tick,end tick)
    resolution     = None   # Ticks per quarter note
    time_signature = {}
    repeats        = []     # Tuples: bar list, delta, skip, repeat, type

    @classmethod
    def fill_bars(cls): # for now assume 4/4
        max_tick = 0
        for mtk in cls.tracks:
            notes = cls.tracks[mtk].notes
            if len(notes) > 0:
                max_tick = max(max(n.at_tick+n.duration for n in notes),max_tick)
        st = 0
        while st < max_tick:
            cls.bars.append( (st,st+4*cls.resolution-1) )
            st += 4*cls.resolution

    @classmethod
    def get_bar_decorators_with_repeat(cls,key_list):
        repeats = cls.repeats
        max_bar = len(cls.bars)

        bar_deco = []
        for i in range(len(MidiTrack.bars)):
            bar_deco.append( { 'info'     :'orig',
                               'pre'      : '',
                               'fmt_voice': '%(bol)s %(key)s %(timesig)s %(pre)s %(bar)s %(post)s  %% %(info)s',
                               'fmt_drum' : '%(bol)s %(timesig)s %(pre)s %(bar)s %(post)s  %% %(info)s',
                               'post'     : ' |',
                               'key'      : '',
                               'timesig'  : '',
                               'bol'      : '',
                               'repeated' : False} )

        for f in repeats:
            c,delta,skip,repeat,typ = f
            if typ == 'volta':
                last_bar = min(c[0]+(1+repeat)*delta,max_bar)-1

                s = '%% %s -> %d repeats of %d bars' % (str(c),repeat+1,delta)
                if skip > 0:
                    s += ' with alternate end(s) of %d bars' % (delta-skip)
                print(s)
                #   delta=4,skip = 0,repeat = 2:
                #                 x  x  x  A  B  C  D  A  B  C  D  A  B  C  D  x  x  x
                #       alt_rep:  +  +  +  A  +  +  B  -  -  -  -  -  -  -  -  +  +  +
                #                        R{          }
                #
                #   delta=4,skip = 2,repeat = 1:
                #                 x  x  x  A  B     C  D  A  B  E  F  x  x  x
                #       alt_rep:  +  +  +  A  B     C  E  -  -  D  F  +  +  +
                #                        R{    } A {    }      {    }}
                #
                #   delta=4,skip = 2,repeat = 2:
                #                 x  x  x  A  B     C  D  A  B  E  F  A  B  G  H  x  x  x
                #       alt_rep:  +  +  +  A  B     C  E  -  -  D  E  -  -  D  F  +  +  +
                #                        R{    } A{{    }      {    }      {    }}
                #
                #   delta=4,skip = 1,repeat = 2:
                #                 x  x  x  A  B  C     D  A  B  C  E  A  B  C  F  x  x  x
                #       alt_rep:  +  +  +  A  +  B     C  -  -  -  G  -  -  -  H  +  +  +
                #                        R{       } A{{ }         { }         { }}
                s = '' if repeat <= 1 else '\\mark "%dx" ' % (repeat+1)
                deco = bar_deco[c[0]]
                deco['info'] = 'alt_rep A %d repeat=%d' % (c[0],repeat)
                deco['pre' ] = '\\repeat volta %d {%s' % (repeat+1,s)
                deco = bar_deco[c[0]+delta-skip-1]
                deco['post'] = '| }' if skip == 0 else '| }\\alternative{'

                if skip > 0:
                    for r in range(1,repeat+2):
                        bar_deco[    c[0]+r*delta-skip          ]['pre' ] = '{'
                        bar_deco[min(c[0]+r*delta-1   ,last_bar)]['post'] = '| }'
                # Blank all repeated bars
                for r in range(2,repeat+2):
                    for deco in bar_deco[c[0]+(r-1)*delta : min(c[0]+r*delta-skip-1,last_bar)+1]:
                        deco['bol'] = '%% SKIP-1: '
                if skip > 0:
                    bar_deco[min(c[0]+(repeat+1)*delta-1,last_bar)]['post'] = '}} |'

            else:
                deco = bar_deco[c[0]]
                print('%%',c,"-> simple repeat")
                deco['info']     = 'simple'
                deco['pre' ]     = '\\repeat percent %d {' % (repeat+1)
                deco['post']     = '}|'
                for deco in bar_deco[c[0]+1:c[0]+repeat+1]:
                    deco['bol'] = '%% SKIP-2: '

        # Add time signatures
        for tick in cls.time_signature:
            for i in range(len(cls.bars)):
                bs,be = cls.bars[i]
                if bs <= tick and tick < be:
                    deco = bar_deco[i]
                    deco['timesig'] = cls.time_signature[tick]
                    break

        # Tuples with (starttick,endtick,key,stats)
        for stick,etick,key,stats in key_list:
            for i in range(len(cls.bars)):
                bs,be = cls.bars[i]
                if bs <= stick and stick < be:
                    deco = bar_deco[i]
                    deco['key'] = '\\key ' + key.lower()
                    break

        return bar_deco

    def __new__(self,pattern,verbose):
        trackname = None
        for e in pattern:
            if type(e) is midi.events.TrackNameEvent:
                trackname = e.text
                break

        instrument = None
        for e in pattern:
            if type(e) is midi.events.InstrumentNameEvent:
                instrument = e.text
                break

        key = '%s_%s' % (trackname,instrument)
        key = key.replace(' ','_')
        if key in MidiTrack.tracks:
            return MidiTrack.tracks[key]

        instance = super().__new__(MidiTrack)

        instance.index          = len(MidiTrack.tracklist)+1
        instance.verbose        = verbose
        instance.key            = key
        instance.trackname      = trackname
        instance.instrument     = instrument
        instance.notecount_128  = [0]*128
        instance.notecount_12   = [0]*12
        instance.notes          = []
        instance.output         = False
        instance.output_piano   = False
        instance.output_drums   = False
        instance.output_voice   = False
        MidiTrack.tracks[key]   = instance
        MidiTrack.tracklist.append(instance)
        return instance

    def __init__(self,pattern,verbose):
        # Be careful here, because self may be a reused instance
        # with same track and instrument name.
        # Reason:
        #    Logic Pro X puts regions in a track into separate midi patterns
        pattern.make_ticks_abs()

        # Get time signature from track
        for e in pattern:
            if type(e) is midi.events.TimeSignatureEvent:
                s = '\\numericTimeSignature\\time %d/%d' \
                            % (e.numerator,e.denominator)
                MidiTrack.time_signature[e.tick] = s

        # Collect all ticks in class variable ticks for all tracks
        for e in pattern:
            if type(e) is midi.events.NoteOnEvent and e.velocity > 0:
                MidiTrack.ticks_set.add(e.tick)
        MidiTrack.ticks=sorted(list(MidiTrack.ticks_set))

        # Logic Pro X seldom uses NoteOff but NoteOn with velocity zero instead
        transient = {}
        for e in pattern:
            if verbose:
                print('%% Event: ',e)

            if type(e) is midi.events.NoteOnEvent and e.velocity > 0:
                if e.pitch in transient:
                    transient[e.pitch].append(e)
                else:
                    transient[e.pitch] = [e]

                self.notecount_128[e.pitch     ] += 1
                self.notecount_12 [e.pitch % 12] += 1

            if type(e) is midi.events.NoteOnEvent and e.velocity == 0 \
                    or type(e) is midi.events.NoteOffEvent:
                if e.pitch not in transient:
                    print('%% NoteOff without NoteOn: ',e)
                else:
                    se = transient[e.pitch].pop(0)
                    if len(transient[e.pitch]) == 0:
                        del transient[e.pitch]

                    note = MidiNote(self,se.pitch,se.velocity,se.tick,e.tick-se.tick)
                    self.notes.append(note)
                    if verbose:
                        print('%% => ',note)
        if len(transient) > 0:
            raise Exception('MIDI-File damaged: Stuck Notes detected')

        self.notes = self.sort_notes(self.notes)

    def sort_notes(self,notes):
        return sorted(notes,key=lambda n:n.at_tick+n.pitch/1000)

    def advise_treble(self): # useful for piano to select bass or treble
        s_bass   = sum(self.notecount_128[:60])
        s_treble = sum(self.notecount_128[60:])
        return s_bass < s_treble

    def trim_notes(self):
        # Trim notes on 1/32 note (1/64 cannot be handled by latter processing)
        res = MidiTrack.resolution // 8
        for n in self.notes:
            dt = ((n.at_tick+res//2)//res)*res - n.at_tick
            if dt != 0:
                print('%% trim note %s by shifting %d ticks (res=%d)' % (n,dt,res))
                n.at_tick  += dt
                n.duration += dt
            dt = ((n.duration+res//2)//res)*res - n.duration
            if dt != 0:
                print('%% trim note %s by %d ticks (res=%d)' % (n,dt,res))
                n.duration += dt
            if n.duration == 0:
                n.duration = res

    def split_same_time_notes_to_same_length(self):
        active   = []
        newnotes = []
        notes = self.notes
        while len(notes) > 0:
            tick      = min(n.at_tick for n in notes)
            same_time = [n for n in notes if n.at_tick == tick]
            dt        = min(n.duration for n in same_time)
            for n in same_time:
                if n.duration == dt:
                    newnotes.append(n)
                    notes.remove(n)
                else:
                    np = MidiNote(n.track,n.pitch,n.velocity,n.at_tick,dt,True)
                    print('%% split %s after %d ticks: %s' % (n,dt,np))
                    newnotes.append(np)
                    n.duration -= dt
                    n.at_tick += dt

        self.notes = self.sort_notes(newnotes)

    def split_notes_at_bar(self):
        newnotes = []
        while(len(self.notes)) > 0:
            n = self.notes.pop(0)
            newnotes.append(n)
            for bs,be in MidiTrack.bars:
                if bs <= n.at_tick and be > n.at_tick:
                    if n.at_tick+n.duration-1 > be:
                        dt = n.at_tick + n.duration - (be + 1)
                        np = MidiNote(n.track,n.pitch,n.velocity,be+1,dt,False)
                        print('%% split note %s by %d ticks at bar %d-%d ticks: %s' % (n,dt,bs,be,np))
                        self.notes.append(np)
                        n.duration -= dt
                        n.extended = True
                    break
        self.notes = self.sort_notes(newnotes)

    def __str__(self):
        s  = 'Track(%s,%s)' % (self.trackname,self.instrument)
        sx = []
        if len(self.notes) > 0:
            sx.append('%d notes' % len(self.notes))
        if len(self.lyrics) > 0:
            sx.append('%d lyric events' % len(self.lyrics))
        sx = ' and '.join(sx)
        if len(sx) > 0:
            s += ' with ' + sx
        return s

    def __repr__(self):
        return 'Track(%s,%s)' % (self.trackname,self.instrument)

