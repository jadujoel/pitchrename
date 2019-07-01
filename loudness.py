import subprocess
from collections import namedtuple


from urllib.request import pathname2url

def os_path_to_ffmpeg_path(path):
    ffmpeg_path = ''
    for char in path:
        if not char.isalnum() and char != "/" and char != "\\":
            char = "\\" + char
        ffmpeg_path += char

    return "{}".format(ffmpeg_path)

def get_loudness(infile, ffprobe_path='ffprobe'):
    # "FFprobe is a multimedia streams analyzer with a
    # command-line interface based on the FFmpeg project libraries"s

    infile_url = os_path_to_ffmpeg_path(infile)
    #print(infile_url)
    cmd = [ffprobe_path,
            '-hide_banner', '-loglevel', 'panic', # Silent mode
            '-f',
            'lavfi',
            "amovie={},ebur128=metadata=1".format(infile_url),
            '-show_frames']

    #print(cmd)
    # ffprobe -v quiet -print_format json -show_format -show_streams "lolwut.mp4" > "lolwut.mp4.json"
    stdout = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=10**8).stdout.read()
    stringout = str(stdout).split('\\')

    LUFS_M, LUFS_S, LUFS_I = [],[],[]
    LRA, LRA_low, LRA_high = [],[],[]
    for v in stringout:
        if not 'nan' in v:
            if 'M=' in v:
                LUFS_M.append(float(v[v.rfind("-"):]))
            elif 'S=' in v:
                LUFS_S.append(float(v[v.rfind("-"):]))
            elif 'I=' in v:
                LUFS_I.append(float(v[v.rfind("-"):]))
            elif 'LRA.low=' in v:
                LRA_low.append(float(v[v.rfind("-"):]))
            elif 'LRA.high=' in v:
                LRA_high.append(float(v[v.rfind("-"):]))
            elif 'LRA=' in v:
                LRA.append(float(v[v.rfind("-"):]))

    return namedtuple('Loudness',
                ['LUFS_I', 'LUFS_S', 'LUFS_M', 'LRA_high', 'LRA_low'])(
                LUFS_I[-1], LUFS_S[-1], LUFS_M[-1], LRA_high[-1], LRA_low[-1])


if __name__ == '__main__':
    #loudness = get_loudness('/Users/admin/Desktop/pitchrename/resources/samples/03_f.aif')
    #loudness = get_loudness('/Users/admin/Downloads/Joel Logic/User Loops/SingleFiles/[ vandalism_ultra_vocals_4 ]/Vandalism_Ultra_Vocals_4_Demo.mp3', ffprobe_path = '/Users/admin/Desktop/pitchrename/ffprobe')
    #loudness = get_loudness('/Users/admin/Downloads/Joel Logic/User Loops/SingleFiles/[ vandalism_ultra_vocals_4 ]/Vandalism_Ultra_Vocals_4_Demo.mp3', ffprobe_path = '/Users/admin/Desktop/pitchrename/ffprobe')
    loudness = get_loudness('/Users/admin/Downloads/Joel Logic/User Loops/SingleFiles/[ vandalism_ultra_vocals_4 ]/[ Vandalism_Ultra_Vocals_4 ]/Voc UV4_02_A.aiff', ffprobe_path = '/Users/admin/Desktop/pitchrename/ffprobe')
    #/Users/admin/Downloads/Joel Logic/User Loops/SingleFiles/[ vandalism_ultra_vocals_4 ]/[ Vandalism_Ultra_Vocals_4 ]/Voc UV4_01_D.aiff
    #loudness = get_loudness("/'Users/'admin/'Downloads/'Joel 'Logic/'User 'Loops/'SingleFiles/'[' 'vandalism_'ultra_'vocals_'4 ']'/'[' 'Vandalism_'Ultra_'Vocals_'4 ']'/'Voc 'UV4_'01_'D.'aiff")

    print(loudness)







