import matplotlib
import matplotlib.pyplot as plt
import librosa
import numpy as np
import subprocess as sp
import os

def load_audio(audio_path, ffmpeg_path='ffmpeg', sr=44100):

    command = [
        ffmpeg_path,
        '-hide_banner', '-loglevel', 'panic',
        #'-ss', '0.0', '-t', '1', #  select first second of file
        '-i', audio_path,
        '-f', 'u32le', # Desired output format, 32 bit little endian
        # fade file, highpass and lowpass (for more accurate pitch results)
        #'-af', 'afade=t=in:d=0.1,afade=t=out:st=0.95:d=0.05,highpass=300,lowpass=8000', #",loudnorm=tp=-2,afftdn=nr=20
        '-acodec', 'pcm_f32le', # format
        '-ar', str(sr), # sample rate
        '-ac', '1', # num channels
        '-']

    pipe = sp.Popen(command, stdout=sp.PIPE, bufsize=10**8)
    raw_audio = pipe.stdout.read()
    audio_array = np.frombuffer(raw_audio, dtype='float32')
    return audio_array, sr


def get_onset_slices(signal, sr=44100):
    oenv = librosa.onset.onset_strength(y=signal, sr=sr)

    # Detect events without backtracking
    try:
        onset_raw = librosa.onset.onset_detect(onset_envelope=oenv,
                                           backtrack=False)
    except Exception:
        return [0], [len(signal)]

    # Backtrack the events using the onset envelope
    #print('len(onset_raw)')
    #print(len(onset_raw))
    if len(onset_raw) == 0:
        return [0], [len(signal)]
    else:
        onset_bt = librosa.core.frames_to_samples(
                    librosa.onset.onset_backtrack(onset_raw, oenv))

    #print('len(onset_bt)')
    #print(len(onset_bt))
    start = np.append(onset_bt, len(signal))

    # Start idx for slices, dont use if slice shorter than dur min
    duration_minimum = sr * 1
    start_cleaned = np.array([]).astype(np.int16)

    for i in range(len(start)-1):
        if start[i+1] - start[i] > duration_minimum:
            start_cleaned = np.append(start_cleaned, start[i])

    if len(start_cleaned) > 2:
        if start_cleaned[-1] == len(signal):
            start_cleaned = start_cleaned[:-2]

    # Stop idx for slices
    stop = np.array([]).astype(np.int16)

    for i in range(1, len(start_cleaned)):
        stop = np.append(stop, start_cleaned[i]-1)

    stop = np.append(stop, len(signal))
    if len(start_cleaned) < 2:
        start_cleaned = [0]
    if len(stop) < 2:
        stop = [len(signal)]

    return start_cleaned, stop

def slice_audio(input_path, output_directory='resources/output'):
    fname_start = input_path.rfind('/') +1
    #if fname_start == -1: fname_start = 0
    input_fname = input_path[ fname_start: input_path.rfind('.') ]
    output_directory = '{}/{}'.format(output_directory, input_fname)
    if not os.path.isdir(output_directory):
        os.mkdir(output_directory)

    signal, sr = load_audio(input_path)
    slices_start, slices_stop = get_onset_slices(signal, sr)

    sliced_audio_paths = []
    for i, (start, stop) in enumerate(zip(slices_start, slices_stop)):
        signal_slice = signal[start:stop]
        output_path = '{}/slice_{}.wav'.format(output_directory, i)
        librosa.output.write_wav(output_path, signal_slice, sr, norm=False)
        sliced_audio_paths.append(output_path)

    return sliced_audio_paths



