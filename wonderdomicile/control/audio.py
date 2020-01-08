import math
import multiprocessing as mp
import statistics
import threading
import time

import madmom
import numpy as np

import bibliopixel.control.control

from wonderdomicile import params, triggers


def db(spec):
    # convert to dB
    np.log10(spec, spec)
    spec *= 20
    return np.max(spec, axis=0)


def audio_process(pipe):
    strm = madmom.audio.signal.Stream(sample_rate=44100, num_channels=1, fps=60)

    spec_procs = madmom.processors.ParallelProcessor([
        None, None, None
    ])
    proc = madmom.processors.SequentialProcessor([
        madmom.audio.spectrogram.SpectrogramProcessor(),
        spec_procs
    ])

    def recv_processors():
        spec3, spec4, spec12 = pipe.recv()
        spec_procs[0] = spec3
        spec_procs[1] = spec4
        spec_procs[2] = spec12
        print("Updated spectrogram processors")

    # Don't start until we have init'd the spectrogram processors
    recv_processors()

    for frame in strm:
        while pipe.poll():
            recv_processors()

        spl = madmom.audio.signal.sound_pressure_level(frame)
        spl = max(-100, spl)

        out = proc.process(frame)
        spec3, spec4, spec12 = out

        # copy to remove madmom's custom subclass
        spec3 = db(np.copy(spec3))
        spec4 = db(np.copy(spec4))
        spec12 = db(np.copy(spec12))

        pipe.send((spl, spec3, spec4, spec12))


class Normalizer:
    def __init__(self, default):
        self.avg = np.copy(default)
        self.raw = np.copy(default)
        self.normalized = np.copy(default)
        self.range = 1
        self.baseline = 0
        self.alpha = 0

    def update_raw(self, raw, range, baseline, alpha):
        if not np.isfinite(raw).all():
            return

        self.raw = raw
        self.range = range
        self.baseline = baseline
        self.alpha = alpha

        if self.avg is None:
            self.avg = raw

        normalized = (raw - self.avg) / range + baseline
        bands_clipping = normalized > 1

        avg_needed_to_unclip = raw - (1 - baseline) * range
        # peaking_ewma = raw * alpha2 + self.avg * (1 - alpha2)
        natural_ewma = raw * alpha + self.avg * (1 - alpha)

        self.avg = np.where(bands_clipping, avg_needed_to_unclip, natural_ewma)
        self.normalized = (raw - self.avg) / range + baseline


class AudioAnalyzer(params.ParamProvider):
    def __init__(self):
        super().__init__()
        self.parent_conn, self.child_conn = mp.Pipe()
        self.proc = None

        self.spl = Normalizer(-100.)
        self.spec3 = Normalizer(np.full(3, -100.))
        self.spec4 = Normalizer(np.full(4, -100.))
        self.spec12 = Normalizer(np.full(12, -100.))

        self.add_param(params.FloatParam('timeconstant', 0.5, 30), 10)
        # self.add_param(FloatParam('timeconstant2', 0.1, 10), 0.5)
        self.add_param(params.FloatParam('db_range', 0.5, 36), 18)
        self.add_param(params.FloatParam('db_baseline', -1, 2), 0.5)

        self.add_param(params.FloatParam('spec_x0min', 0, 300), 30)
        self.add_param(params.FloatParam('spec_x1', 20, 500), 250)
        self.add_param(params.FloatParam('spec_x2', 200, 5000), 2000)
        self.add_param(params.FloatParam('spec_x3', 20, 10000), 6000)
        self.add_param(params.FloatParam('spec_x9max', 10000, 30000), 20000)

        self.value_change_trigger = triggers.ValueChangeTrigger()
        # hack: force first step() to trigger
        self.value_change_trigger.step(0)

    def update_spectrogram_processors(self):
        spec3 = madmom.audio.spectrogram.MultiBandSpectrogramProcessor(
            [self.param('spec_x1'), self.param('spec_x3')],
            fmin=self.param('spec_x0min'),
            fmax=self.param('spec_x9max')
        )
        spec4 = madmom.audio.spectrogram.MultiBandSpectrogramProcessor(
            [self.param('spec_x1'), self.param('spec_x2'), self.param('spec_x3')],
            fmin=self.param('spec_x0min'),
            fmax=self.param('spec_x9max')
        )
        xovers = np.concatenate([
            np.geomspace(self.param('spec_x0min'), self.param('spec_x1'), 4)[1:],
            np.geomspace(self.param('spec_x1'), self.param('spec_x2'), 4)[1:],
            np.geomspace(self.param('spec_x2'), self.param('spec_x3'), 4)[1:],
            np.geomspace(self.param('spec_x3'), self.param('spec_x9max'), 4)[1:-1],
        ])
        spec12 = madmom.audio.spectrogram.MultiBandSpectrogramProcessor(
            xovers,
            fmin=self.param('spec_x0min'),
            fmax=self.param('spec_x9max')
        )
        self.parent_conn.send((spec3, spec4, spec12))

    def step(self):
        if self.value_change_trigger.step((
                self.param('spec_x0min'), self.param('spec_x1'), self.param('spec_x2'),
                self.param('spec_x3'), self.param('spec_x9max'))):
            self.update_spectrogram_processors()

        spl_raw = spec3_raw = spec4_raw = spec12_raw = None
        while self.parent_conn.poll():
            spl_raw, spec3_raw, spec4_raw, spec12_raw = self.parent_conn.recv()

        delta_t = 1/60
        alpha = delta_t / (delta_t + self.param('timeconstant'))
        # alpha2 = delta_t / (delta_t + self.param('timeconstant2'))
        range = self.param('db_range')
        baseline = self.param('db_baseline')

        if spec3_raw is not None:
            self.spec3.update_raw(spec3_raw, range, baseline, alpha)
        if spec4_raw is not None:
            self.spec4.update_raw(spec4_raw, range, baseline, alpha)
        if spec12_raw is not None:
            self.spec12.update_raw(spec12_raw, range, baseline, alpha)
        if spl_raw is not None:
            self.spl.update_raw(spl_raw, range, baseline, alpha)

    def start(self):
        self.proc = mp.Process(target=audio_process, args=(self.child_conn,))
        self.proc.start()

        self.stop = False
        self.thread = threading.Thread(target=self.run_thread, args=())
        self.thread.start()

    def stop(self):
        self.proc.terminate()
        self.stop = True
        self.thread.join()

    def run_thread(self):
        while not self.stop:
            self.step()
            time.sleep(1./60)


class BeatTracker(params.ParamProvider):
    def __init__(self):
        super().__init__()

        self._beat_timestamp = 0
        self._beat_period = 60 / 120
        self._downbeat_timestamp = 0
        self._downbeat_timestamp_unquantized = 0
        self._tap_intervals = []
        self.add_param(params.FloatParam('bpm', 45, 220), 60)
        self.add_param(params.IntParam('time_signature', 1, 8), 4)

        # [0, 1) float, 0 on beat, progresses to 1 at the end of the beat
        self.beat_raw = 0

        # [0, 1) float, 0 on downbeat, progresses to 1 at the end of the measure
        self.downbeat_raw = 0

        # [0, time_signature) float
        self.beat_count = 0

    def step(self):
        now = time.perf_counter()

        if self.read_and_clear_trigger('Tap BPM'):
            interval = now - self._beat_timestamp
            self._beat_timestamp = now

            if interval > 2:  # first tap
                self._downbeat_timestamp_unquantized = now
                self._tap_intervals = []
            else:
                self._tap_intervals.append(interval)

                self.set_param('bpm', 60 / statistics.mean(self._tap_intervals))

        self._beat_period = 60 / self.param('bpm')
        self.quantize_downbeat_timestamp()

        x = (now - self._beat_timestamp) / self._beat_period
        self.beat_raw = x - math.floor(x)

        y = (now - self._downbeat_timestamp) / (self._beat_period * self.param('time_signature'))
        self.downbeat_raw = y - math.floor(y)

        self.beat_count = self.downbeat_raw * self.param('time_signature')

    def quantize_downbeat_timestamp(self):
        """Find closest beat to put downbeat on

        TODO: make this more stable when triggered far away from the last marked unquantized downbeat
        """
        beats_since_ts = (self._downbeat_timestamp_unquantized - self._beat_timestamp) / self._beat_period
        self._downbeat_timestamp = round(beats_since_ts) * self._beat_period + self._beat_timestamp


# what a hack, to kinda use Controls
GlobalAnalyzer = AudioAnalyzer()


class AudioAnalyzerControl(bibliopixel.control.control.Control):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def start(self):
        GlobalAnalyzer.start()

    def stop(self):
        GlobalAnalyzer.stop()
