# Transience Spectrogram
import numpy as np
#from fourier import stftAnal
from librosa import load, stft
from woff import Bark
import matplotlib.pyplot as plt
import matplotlib
import copy
import scipy.signal
from cbfilter import *
#from preprocess import *

# def stft(x, n_fft, hop_length, win_length, window='hann', center=True, pad_mode='reflect'):
#     #w = scipy.signal.windows.get_window(window, Nx=win_length, fftbins=True)
#     f, t, Zxx = scipy.signal.stft(x, fs=1.0, window='hann', nperseg=hop_length, nfft=n_fft)
#     print(Zxx.shape)
#     return Zxx

def timeareas(target_len, hop_len):
    tl, hl = target_len, hop_len
    print('\n >> Timeareas')
    print(' Target len: ', tl)
    print(' hop_len: ', hl)

    num_hops = tl//hl
    if num_hops == 0:
        return [0], [tl]

    #  float - int
    if tl/hl - num_hops != 0:
        num_hops += 1

    ts = []
    te = []
    for i in range(num_hops):
        ts.append(i*hl)
        te.append((i+1)*hl)
    te[-1] = tl
    return ts, te

def plots(spec, yscale='symlog', fs=44100):
    # back = matplotlib.get_backend()
    # matplotlib.use('TkAgg')
    # matplotlib.use('TkAgg')

    threshhz = 500
    maxfreq = fs//2
    maxbin = spec.shape[0]
    linthreshy = maxbin/maxfreq * threshhz

    n=1
    fig_a, axes = plt.subplots(nrows=1,
                             ncols=1,
                             figsize=(12.8*0.9,8*0.9),
                             sharex=True,
                             sharey=True,
                             #squeeze=True,
                             #gridspec_kw=None)
                             )

    axes.set_yscale(yscale,linthreshy=linthreshy)

    axes.matshow(spec,
                    interpolation='nearest',
                    aspect='auto',
                    origin='lower',
                    cmap=plt.cm.afmhot
                    )
    # plt.show()
    plt.savefig('Spect.png')


## Load wav
print('loading wav')
y, fs = load('pitchrename.wav', mono=True, sr=44100, duration=200)
y = y / np.max(y)
maxfreq = fs//2

## Make Spectrogram ##
wlen_ms = 12
wlen = int(wlen_ms * fs/1000)
if wlen % 2 is not 0:
    wlen += 1
nfft = 8192
#nfft = 2048
maxbin = nfft//2+1
H_ms = 6 # Hop length
H = wlen//2 # int(H_ms * fs/1000)

print('Making spectrogram')
mx = np.abs(stft(y, n_fft=nfft, hop_length=H, win_length=wlen, window='hann', center=True, pad_mode='reflect'))
mx /= np.max(mx)

print('Window length {}, hop length {}, num fft {}'.format(wlen, H, nfft))
print('output stft shape {}'.format(mx.shape))

# Critical bands - Bark spectrogram
nfilts = 24
rasta = Bark(nfft=nfft+2, fs=fs, nfilts=nfilts, version="rasta", width=1.0, minfreq=0, maxfreq=maxfreq)
cb = rasta.forward(mx)

# integrated energy
ie = cb ** (1/8)
n_f = mx.shape[0] # num frequencies
n_b = cb.shape[0] # num bins
n_t = cb.shape[1] # num frames - time axis

plt.plot(ie.T)
plt.savefig('ie.png')
plt.close()

# cross-correlating filter
h = np.array([-1, -1, -1, 0, 1, 1, 1])
v = np.zeros_like(ie)
for b in range(n_b):
    v[b,:] = np.correlate(ie[b,:], h, mode='same')

# transcience
ts = np.zeros_like(v)
for b in range(n_b):
    for t in range(n_t):
        if v[b, t] >= 0:
            ts[b, t] = v[b, t]
        else:
            ts[b, t] = np.abs(v[b, t] / 10)

plt.plot(ts.T)
plt.savefig('ts.png')
plt.close()

# potential window lengths - r
r_ms = np.array([12, 24, 48, 96])
r = [int(x*fs/1000) for x in r_ms]
print('r', r)

# Get sizes
tx = np.abs(stft(y, n_fft=nfft, hop_length=H, win_length=r[0], window='hann', center=True, pad_mode='reflect'))
n_f = tx.shape[0] # num frequencies
n_t = tx.shape[1] # num frames - time axis
n_r = len(r)      # num window lengths

plt.plot(tx.T)
plt.savefig('tx.png')
plt.close()

# Make spectrograms with different window lengths
aftr = np.zeros((n_f, n_t, n_r))
for i in range(len(r)):
    print('making spectro {} out of {}'.format(i, len(r)))
    aftr[:, :, i] = np.abs(stft(y, n_fft=nfft, hop_length=H, win_length=r[i], window='hann', center=True))

def sortByMagnitude(aftr, n_t, n_r):
    # Sort with highest magnitude descending
    mt = []
    for t in range(n_t):
        m = []
        for r in range(n_r):
            m.append(np.max(aftr[:, t, r]))
        mt.append(m)
    mt = np.array(mt)

# Energy smearing
# The numerator of the fraction evaluates the first moment of the statistical distribution of squared magnitudes
# the first moment is the mean,
epsilon = np.finfo(float).eps
air = aftr # should be sorted but seems to be already by chance or whaatevs

# plt.plot(air)
# plt.savefig('air.png')
# plt.close()

num_freqbins = 24

fa = int((nfft//2+1) / num_freqbins) # freqarea in bins
ta_ms = 48
ta = ta_ms // H_ms # Time area in frames

bs, be = nfilt_criticalbins(nfilts, nfft, fs) # Get start and stop bins for critical bands
ts, te = timeareas(target_len=air.shape[1], hop_len=ta) # Start and stop for time areas

# Find smearing for each band
n_fa = int(np.floor(n_f/fa)) # num frequency-areas
n_ta = int(np.floor(n_t/ta)) # num time-areas
es = np.zeros((n_fa, n_ta, n_r)) # energysmearing

#plt.plot(es)
#plt.savefig('es.png')
#plt.close()

for f in range(n_fa):
    for t in range(n_ta):
        for r in range(n_r):
            nom = np.mean(air[bs[f]:be[f], ts[t]:te[t], :])
            den = np.sqrt(
                    np.sum(air[bs[f]:be[f], ts[t]:te[t], r])
                    ) + epsilon
            es[f, t, r] = nom / den

best_idx = np.zeros((n_fa, n_ta, 1))
for f in range(n_fa):
    for t in range(n_ta):
        temp = es[f,t,:]
        idx = int(np.where(temp == np.min(temp))[0][0])
        best_idx[f,t,:] = idx

# Combine the best spectrograms for each area
combine = np.zeros((n_f, n_t))
for f in range(n_fa):
    for t in range(n_ta):
        for r in range(n_r):
            combine[bs[f]:be[f], ts[t]:te[t]] = air[bs[f]:be[f],
                                                ts[t]:te[t],
                                                int(best_idx[f,t,:][0])]

print('great success')
# plt.plot(combine)
# plt.savefig('combine.png')
# plt.close()
plots(combine)

