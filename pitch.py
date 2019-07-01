from numpy import nan as np_nan, sum as np_sum

from parselmouth import Sound as pm_Sound
from parselmouth.praat import call as pm_praat_call
from hzmidi import hzmididict

def get_root_pitch(signal):
    # High notes
    # praat manual: http://www.fon.hum.uva.nl/praat/manual/Sound__To_Pitch__ac____.html
    snd = pm_Sound(signal) # Load sound into parsel class

    # # ac = auto correlation method
    # # cc = cross correlation method
    pitch = snd.to_pitch_ac(
        time_step = None, # the measurement interval (frame duration), in seconds. If you supply 0, Praat will use a time step of 0.75 / (pitch floor), e.g. 0.01 seconds if the pitch floor is 75 Hz; in this example, Praat computes 100 pitch values per second.
        pitch_floor = 27.0, # candidates below this frequency will not be recruited. This parameter determines the effective length of the analysis window: it will be 3 longest periods long, i.e., if the pitch floor is 75 Hz, the window will be effectively 3/75 = 0.04 seconds long.
        pitch_ceiling = 3420.0,
        very_accurate = True, # if off, the window is a Hanning window with a physical length of 3 / (pitch floor). If on, the window is a Gaussian window with a physical length of 6 / (pitch floor), i.e. twice the effective length.
        max_number_of_candidates=15,
        silence_threshold=0.03, # frames that do not contain amplitudes above this threshold (relative to the global maximum amplitude), are probably silent.
        voicing_threshold = 0.45, # the strength of the unvoiced candidate, relative to the maximum possible autocorrelation. To increase the number of unvoiced decisions, increase this value.
        octave_cost = 0.2, #0.01 degree of favouring of high-frequency candidates, relative to the maximum possible autocorrelation. This is necessary because even (or: especially) in the case of a perfectly periodic signal, all undertones of F0 are equally strong candidates as F0 itself. To more strongly favour recruitment of high-frequency candidates, increase this value.
        octave_jump_cost = 0.35, # degree of disfavouring of pitch changes, relative to the maximum possible autocorrelation. To decrease the number of large frequency jumps, increase this value. In contrast with what is described in the article, this value will be corrected for the time step: multiply by 0.01 s / TimeStep to get the value in the way it is used in the formulas in the article.
        voiced_unvoiced_cost = 0.01 #0.14 degree of disfavouring of voiced/unvoiced transitions, relative to the maximum possible autocorrelation. To decrease the number of voiced/unvoiced transitions, increase this value. In contrast with what is described in the article, this value will be corrected for the time step: multiply by 0.01 s / TimeStep to get the value in the way it is used in the formulas in the article.
        )

    # Get average pitch
    pitch_values = pitch.selected_array['frequency']
    pitch_values_cleaned = pitch_values[pitch_values>0]
    pitch_values[pitch_values==0] = np_nan
    quantile = pm_praat_call(pitch, "Get quantile", 0.0, 0.0, 0.5, "Hertz")

    # Different settings works better for low notes.
    if quantile < 1000 or np_sum(pitch_values_cleaned) == 0:
        snd = pm_Sound(signal) # Load sound into parsel class
        pitch = snd.to_pitch(
            time_step = None,
            pitch_floor = 27.0,
            pitch_ceiling = 5000.0,
            )
        pitch_values = pitch.selected_array['frequency']
        pitch_values_cleaned = pitch_values[pitch_values>0]
        pitch_values[pitch_values==0] = np_nan
        quantile = pm_praat_call(pitch, "Get quantile", 0.0, 0.0, 0.5, "Hertz")

    # Load list of temperated notes and corresponding hz
    hzkeys = []
    for k, (v, n) in hzmididict.items():
        hzkeys.append(k)

    closest_hzkey = min(hzkeys, key=lambda x:abs(x-quantile))
    root = hzmididict[closest_hzkey][0]
    note = hzmididict[closest_hzkey][1]
    return root
