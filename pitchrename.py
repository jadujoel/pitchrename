# Todo : Slice into regions
#       fix paths correct when sublime, terminal & exe
#       ## no need to crawl subdirectories.

# Python included libs:
import os
import sys
import subprocess as sp
import shutil
import argparse
import time
import itertools

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning) # To ignore annoying librosa warning

# External Libs
import numpy as np

# User made:
import timedecorator as td # for printing times to optimize performance of this program.
from loudness import get_loudness
from pitch import get_root_pitch


get_loudness = td.profile(get_loudness)
get_root_pitch = td.profile(get_root_pitch)

@td.profile
def os_path_to_ffmpeg_path(path):
    ffmpeg_path = ''
    for char in path:
        if not char.isalnum() and char != "/" and char != "\\":
            char = "\\" + char
        ffmpeg_path += char

    return "{}".format(ffmpeg_path)

@td.profile
def sizeof_fmt(num, suffix='B'):
    # For printing memory usage
    ''' By Fred Cirera, after https://stackoverflow.com/a/1094933/1870254'''
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

@td.profile
def progbar(count, count_max, progbar_length = 50, text='Progress'):
    progress = count / count_max
    progbar_length = 50
    progbar = int(progress * progbar_length)
    print('  {} {:2.1%} [{}{}]'.format(text, progress, '=' * progbar, ' '* int(progbar_length - progbar)), end="\r")

@td.profile
def print_main_dict(main_dict):
    for key, value in main_dict.items():
        for obj in value:
            print('',
                    'root', obj.root,
                    'kmin', obj.key_min,
                    'kmax', obj.key_max,
                    'vmin', obj.vel_min,
                    'vmax', obj.vel_max,
                    'path', obj.path,
                    'name', obj.name,
                    'path out', obj.path_output
                    )

@td.profile
def velocity_from_loudness(loudness):

    nl = len(loudness)
    if nl == 1:
        # If only one sample for that root key,
        # then set to fill entire velocity range
        vels_min = [0]
        vels_max = [127]

    elif nl == 0:
        raise Exception('length of louds is bad')

    else:
        # Normalize to spread velocity from loudness
        vels_max = np.round(normalized(np.array(loudness), 127/nl, 127)).astype(np.int16)

        # Set vel min list to fill range until next max
        vels_min = np.zeros_like(vels_max)
        vels_max_sorted = sorted(vels_max)
        for i, val in enumerate(vels_max):
            idx = np.where(vels_max_sorted == val)[0][0]
            if idx > 0:
                vels_min[i] = vels_max_sorted[idx-1] + 1

        vels_max_sorted.clear()
    return vels_min, vels_max

@td.profile
def keyrange_from_unique_roots(roots):
    # Remove duplicates
    roots_cleaned = sorted(list(dict.fromkeys(roots)))

    min_key = np.zeros_like(roots_cleaned, dtype=np.int16)
    for i in range(1, len(roots_cleaned)):
        min_key[i] = int(roots_cleaned[i])

    max_key = np.zeros_like(roots_cleaned, dtype=np.int16)
    for i in range(len(roots_cleaned)-1):
        max_key[i] = int(roots_cleaned[i+1]) -1
    max_key[-1] = 127

    keyranges_dict = {}
    for i, root in enumerate(roots_cleaned):
        keyranges_dict[root] = (min_key[i], max_key[i])

    return keyranges_dict

@td.profile
def normalized(array, x, y):
    mini = np.min(array)

    range1 = np.max(array) - mini
    if range1 == 0:
        # to avoid potential divide by zero
        range1 = 2e-11

    array = (array - mini) / range1

    range2 = y - x

    normalized = (array * range2) + x

    return normalized

@td.profile
def parse_args():
    parser = argparse.ArgumentParser(description='Rename files for kontakt auto-map')
    parser.add_argument('-i', default=None, help='provide an input folder')
    parser.add_argument('-o', default=None, help='provide an output folder')
    parser.add_argument('-slice', default=False, help='True or False, if you want to slice into separate files at transients or not')
    args = parser.parse_args()

    try:
        correct_input = os.path.isdir(args.i)
    except Exception as e:
        print(e)
        correct_input = False
    while not correct_input:
        print('Input is not detected to be an actual folder.')
        args.i = input('Please provide an input folder. You can do this by dragging a folder from finder into this terminal and press enter. \n')
        while args.i.endswith(' '): # Remove trailing whitespaces
            args.i = args.i[:-1]
        correct_input = os.path.isdir(args.i)

    try:
        correct_output = os.path.isdir(args.o)
    except Exception as e:
        print(e)
        correct_output = False
    while not correct_output:
        print('output is not detected to be an actual folder.')
        args.o = input('Please provide an output folder. You can do this by dragging a folder from finder into this terminal and press enter. \n')
        while args.o.endswith(' '): # Remove trailing whitespaces
            args.o = args.o[:-1]
        correct_output = os.path.isdir(args.o)

    print('selected input folder: ', args.i)
    print('selected output folder: ', args.o)
    print('Thanks! moving on \n')
    return args

@td.profile
def dBFS_float32(sample_level):
    dBFS = 20 * np.log10(sample_level )
    return dBFS

@td.profile
def find_audio_files(input_dir):
    # Find files
    # ffmpeg accepted Extensions / Codecs
    accepted_extensions = ('.aa', '.aac', '.ac3', '.acm', '.aiff', '.aif',
                           '.caf', '.dss', '.dts', '.dtshd', '.flac',
                           '.mp2', '.mp3', '.mp4', '.mpeg', '.oga', '.ogg',
                           '.oma', '.opus', '.sox', '.wav')


    print('Find Files in ', input_dir)
    input_paths = []
    for root, dirs, files in os.walk(input_dir):
        for f in files:
            if f.endswith(accepted_extensions):
                input_paths.append(root + '/' + f)

    input_paths.sort()

    if len(input_paths)<1:
        print('No samples found, exiting program')
        sys.exit()

    else:
        print('Input samples found: ', len(input_paths))
        #for path in input_paths:
        #    print ('    ', path)

    return input_paths

@td.profile
def load_audio(audio_path, ffmpeg_path='ffmpeg', sr=44100):
    #/'Users/'admin/'Downloads/'Joel 'Logic/'User 'Loops/'SingleFiles/'[' 'vandalism_'ultra_'vocals_'4 ']'/'Vandalism_'Ultra_'Vocals_'4_'Demo.'mp3
    command = [
        ffmpeg_path,
        '-hide_banner', '-loglevel', 'panic',
        '-ss', '0.0', '-t', '1', #  select first second of file
        #'-i',  os_path_to_ffmpeg_path(audio_path),
        '-i',  audio_path,
        '-f', 'u32le', # Desired output format, 32 bit little endian
        # fade file, highpass and lowpass (for more accurate pitch results)
        '-af', 'afade=t=in:d=0.1,afade=t=out:st=0.95:d=0.05,highpass=300,lowpass=8000', #",loudnorm=tp=-2,afftdn=nr=20
        '-acodec', 'pcm_f32le', # format
        '-ar', str(sr), # sample rate
        '-ac', '1', # num channels
        '-']
    #print(command)
    pipe = sp.Popen(command, stdout=sp.PIPE, bufsize=10**8)
    raw_audio = pipe.stdout.read()
    audio_array = np.frombuffer(raw_audio, dtype='float32')
    return audio_array, sr

class Param(object):
    def __init__(self):
        self.path = ''
        self.path_output = ''
        self.name = ''
        self.root = 0
        self.loud = 0
        self.vel_min = 0
        self.vel_max = 0
        self.key_min = 0
        self.key_max = 0

@td.profile
def main(args):

    input_dir = args.i
    output_dir = args.o

    ############### Paths #################

    basedir = os.path.dirname(os.path.abspath(__file__))
    #basedir = os.path.dirname(sys.argv[0])
    print('Basedir, ', basedir)

    ffmpeg_path = '{}/ffmpeg'.format(basedir)
    ffprobe_path = '{}/ffprobe'.format(basedir)
    print('ffmpeg path', ffmpeg_path)

    input_paths = find_audio_files(input_dir)

    ############### slicing #################
    if args.slice:
        sliced_audio_paths = []
        import slicing
        for i, path_in in enumerate(input_paths):
            progbar(text='Slicing audio {} >'.format(path_in), count=i, count_max=len(input_paths))
            sliced_audio_paths.append(slicing.slice_audio(path_in, output_dir))

        try: sliced_audio_paths = list(itertools.chain.from_iterable(sliced_audio_paths))
        except Exception as e: print(e)

        print(len(sliced_audio_paths))
        for path in sliced_audio_paths:
            print(path)

    ############### Root Pitch and Loudness #################

    print('Loading audio, calculating root pitch and LUFS')

    main_dict = {}
    unique_roots = []
    count = 0
    for path_in in input_paths:
        progbar(count=count, count_max=len(input_paths)-1, text='Progress: ')
        count += 1

        signal, sr = load_audio(path_in, ffmpeg_path)

        o = Param()
        o.path = path_in
        o.root = get_root_pitch(signal)
        o.loud = get_loudness(path_in, ffprobe_path)[0]
        #print('loudness:', o.loud)

        try:
            main_dict[o.root].append(o)
        except KeyError:
            main_dict[o.root] = [o]
            unique_roots.append(o.root)

    ############### Key min, key max #################
    print('\nunique root keys found', unique_roots)
    keyranges_dict = keyrange_from_unique_roots(unique_roots)
    for key, value in main_dict.items():
        for obj in value:
            obj.key_min = keyranges_dict[key][0]
            obj.key_max = keyranges_dict[key][1]

    ############### Velocity #################

    for key, value in main_dict.items():

        # Select all loudness for this root
        louds = np.array([])
        for obj in value:
            louds = np.append(louds, obj.loud)

        # Set velocity based on loudness for this root
        vels_min, vels_max = velocity_from_loudness(louds)

        # Store velocity in main dict per object
        for i, obj in enumerate(value):
            obj.vel_min = vels_min[i]
            obj.vel_max = vels_max[i]

    ############### Output Name #################

    for key, value in main_dict.items():
        for obj in value:
            naming_scheme = '{} {} {} {} {}'.format(obj.root, obj.key_min, obj.key_max, obj.vel_min, obj.vel_max)
            extension = obj.path[obj.path.rfind('.'):]
            obj.path_output = '{}/{}{}'.format(output_dir, naming_scheme, extension)

    ############### Copy files (with new names) ################

    print('Copying files with new names.')
    print('Filename structure is:  Root LowKey-HighKey VelocityMin-Velocity Max')
    for key, value in main_dict.items():
        for obj in value:
            shutil.copyfile(obj.path, obj.path_output)
            print('     {}  >  {}'.format(obj.path, obj.path_output))

    # print_main_dict(main_dict)

    print('memory usage')
    for name, size in sorted(((name, sys.getsizeof(value)) for name,value in locals().items()),
                         key= lambda x: -x[1])[:10]:
        print("{:>30}: {:>8}".format(name,sizeof_fmt(size)))

    print('Great Success!')
    print('')

if __name__ == '__main__':
    distribute = True
    if not distribute:
        args = argparse.ArgumentParser(description='Rename files for kontakt auto-map').parse_args()
        args.i = '/Users/admin/Downloads/Joel/Logic/User/Loops/SingleFiles/[vandalism_ultra_vocals_4]/[Vandalism_Ultra_Vocals_4]'
        args.i = '/Users/admin/Downloads/Joel Logic/User Loops/SingleFiles/[ vandalism_ultra_vocals_4 ]'
        args.o = '/Users/admin/Desktop/pitchrename/resources/output'
        args.slice = False
    if distribute:
        args = parse_args()
    main(args)
    td.print_prof_data()

