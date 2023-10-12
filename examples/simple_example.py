
import numpy as np
from commpy.utilities  import upsample
from optic.models.devices import mzm, photodiode
from optic.models.channels import linFiberCh
from optic.comm.modulation import modulateGray
from optic.dsp.core import firFilter, pulseShape, signal_power
from optic.core import parameters
from scipy.special import erfc

## Intensity modulation (IM) with On-Off Keying (OOK)

# simulation parameters
SpS = 16    # samples per symbol
M = 2       # order of the modulation format
Rs = 10e9   # Symbol rate
Fs = SpS*Rs # Signal sampling frequency (samples/second)
np.random.seed(seed=123) # fixing the seed to get reproducible results

# MZM parameters
Vpi = 2
Vb = -Vpi/2
Pi_dBm = 0 # laser optical power at the input of the MZM in dBm
Pi = 10**(Pi_dBm/10)*1e-3 # convert from dBm to W

# linear fiber optical channel parameters
L = 90         # total link distance [km]
alpha = 0.2        # fiber loss parameter [dB/km]
D = 16         # fiber dispersion parameter [ps/nm/km]
Fc = 193.1e12  # central optical frequency [Hz]

# photodiode parameters
paramPD = parameters()
paramPD.ideal = False
paramPD.B = Rs
paramPD.Fs = Fs

## Simulation
print('\nStarting simulation...')

# generate pseudo-random bit sequence
bitsTx = np.random.randint(2, size=100000)

# generate 2-PAM modulated symbol sequence
symbTx = modulateGray(bitsTx, M, 'pam')    

# upsampling
symbolsUp = upsample(symbTx, SpS)

# typical NRZ pulse
pulse = pulseShape('nrz', SpS)
pulse = pulse/max(abs(pulse)) # normalize to 1 Vpp

# pulse shaping
sigTx = firFilter(pulse, symbolsUp)

# optical modulation
Ai = np.sqrt(Pi)*np.ones(sigTx.size) # ideal cw laser envelope
sigTxo = mzm(Ai, sigTx, Vpi, Vb)

# Linear fiber channel model 
sigCh = linFiberCh(sigTxo, L, alpha, D, Fc, Fs)

# Direct-detection (DD) pin receiver model

# noisy photodiode (thermal noise + shot noise + bandwidth limitation)
I_Rx = photodiode(sigCh, paramPD)
I_Rx = I_Rx/np.std(I_Rx)

# capture samples in the middle of signaling intervals
I_Rx = I_Rx[0::SpS]

# get received signal statistics
I1 = np.mean(I_Rx[bitsTx==1]) # average value of I1
I0 = np.mean(I_Rx[bitsTx==0]) # average value of I0

σ1 = np.std(I_Rx[bitsTx==1]) # standard deviation σ1 of I1
σ0 = np.std(I_Rx[bitsTx==0]) # standard deviation σ0 of I0

Id = (σ1*I0 + σ0*I1)/(σ1 + σ0) # optimal decision threshold
Q = (I1-I0)/(σ1 + σ0) # factor Q

# apply the optimal decision rule
bitsRx = np.empty(bitsTx.size)
bitsRx[I_Rx> Id] = 1
bitsRx[I_Rx<= Id] = 0

# calculate the BER
err = np.logical_xor(bitsRx, bitsTx)
BER = np.mean(err) 

print('\nReceived signal parameters:')
print(f'I0 = {I0:.2f}')
print(f'I1 = {I1:.2f}')
print(f'σ0 = {σ0:.2f}')
print(f'σ1 = {σ1:.2f}')
print(f'Optimal decision threshold Id = {Id:.2f}')
print(f'Q = {Q:.2f} \n')

Pb = 0.5 * erfc(Q / np.sqrt(2))  # theoretical error probability
print(f'Number of counted errors = {err.sum()}')
print(f'BER = {BER:.2e}')
print(f'Pb = {Pb:.2e}')
