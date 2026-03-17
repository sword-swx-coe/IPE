import numpy as np
from argparse import ArgumentParser, RawTextHelpFormatter
from datetime import datetime, timedelta
import os
from input_helpers import reformat_date
from input_helpers import get_gfz
from input_helpers import download_ap107_file, read_ap107_file
from input_helpers import download_omni_data, clean_omni, parse_omni_data, write_swmf_imf_file
from input_helpers import download_sme_data, write_sme_file

def get_args():
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter,
                            description="Download data and create input files for IPE")
    parser.add_argument('start', type=str,
                        help="Start date[time]")
    parser.add_argument('end', type=str,
                        help="End date[time]\n"
                        "Date[time] format is yyyy-mm-dd[THH:MM:SSZ] or yyyymmdd[Thh:mm:ssZ]")

    parser.add_argument('-dt', default=60, type=int,
                        help='Time cadence, in seconds, to output data at (default=60)')

    parser.add_argument('-v', '--verbose', action='store_true')

    # For use with MILE we need IMF & AE in separate files
    # These will be written in addition to the regular ipe input file!
    parser.add_argument('-mile', action='store_true',
                        help='Include to also write IMF & AE files for use with MILE')
    parser.add_argument('-sme', action='store_true',
                        help='Use SuperMAG instead of OMNI for AE/AU/AL')

    return parser.parse_args()


def main(args):
    doVerbose=args.verbose

    t_start = reformat_date(args.start)
    t_end = reformat_date(args.end)
    if doVerbose:
        print(f"Getting data from {t_start} -> {t_end}")

    # Create array of output times
    dt_nSec = int((t_end  - t_start).total_seconds())+1
    dt_arr = np.arange(0, dt_nSec, 60)
    t_out = [t_start + timedelta(seconds=int(dt)) for dt in dt_arr]
    nTimes = len(t_out)

    # Get f107 & f107a - one value per day
    f107 = get_f107(t_start, t_end, doVerbose)
    f107 = interp_data(f107, t_out)

    # Get Kp - one value per 3 hours
    Kp = get_gfz(t_start, t_end, 'Kp')
    Kp = interp_data(Kp, t_out)

    # Get IMF (roughly every 1 min)
    imf = get_imf(t_start, t_end, verbose=doVerbose)
    imf = interp_data(imf, t_out)
    # If we want to use supermag for ae, do that
    # And replace omni's ae/au/al values
    if args.sme:
        if doVerbose:
            print("Attempting to download SME data...")
        sme = download_sme_data(t_start, t_end)
        sme = interp_data(sme, t_out)
        imf['ae'] = sme['ae']
        imf['al'] = sme['al']
        imf['au'] = sme['au']
    imf['hp'] = calc_hp(imf['ae'])

    allData = dict(
        times   = t_out,
        f107    = f107['f107'],
        kp      = Kp['Kp'],
        f10flag = np.zeros(nTimes, dtype=int) + 2,
        kpflag  = np.zeros(nTimes, dtype=int) + 1,
        f107a   = f107['f107a'],
        kpAvg   = Kp['KpAvg'],
        hpn     = imf['hp'],
        hpin    = np.zeros(nTimes, dtype=int) - 1,
        hps     = imf['hp'],
        hpis    = np.zeros(nTimes, dtype=int) - 1,
        bt      = imf['btot'],
        bangle  = imf['bangle'],
        vx      = np.abs(imf['vx']),
        bz      = imf['bz'],
        n       = imf['n'],
    )

    write_ipe_data(t_start, allData)

    if args.mile:
        filespec = f"_{t_start.strftime("%Y%m%d")}.txt"
        write_swmf_imf_file(imf, 'imf'+filespec)
        write_sme_file(imf, 'ae'+filespec)

    return

def write_ipe_data(start, data):

    filename = start.strftime("ipe_%Y%m%d.txt")
    print(f"Writing IPE file: '{filename}'")
    # Not sure this is necessary, but im afraid to do anything different
    header= """Issue Date
Flags:  0=Forecast, 1=Estimated, 2=Observed

Date_Time                   F10          Kp     F10Flag      KpFlag  F10_41dAvg   24HrKpAvg    NHemiPow NHemiPowIdx    SHemiPow SHemiPowIdx       SW_Bt    SW_Angle SW_Velocity       SW_Bz      SW_Den
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
"""

    times = data.pop('times')
    with open(filename, 'w') as f:
        f.write(header)
        for iLine, time in enumerate(times):
            line = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            for col in data:
                datum = data[col][iLine]
                if int(datum) == datum:
                    line += str(datum).rjust(12, ' ')
                else:
                    # cols are 12 wide with a space preceding the digits
                    if datum < 1000:
                        line += " %11.7f" % (datum)
                    else: # not sure if IPE is decimal dependent
                        line += " %11.6f" % (datum)
            line += '\n'
            f.write(line)
    return


def interp_data(data, to_times):
    """
    Linear interpolation from any cadence to `to_times` - a datetime array
    """
    in_times = data.pop('times')
    new_data = {}
    new_data['times'] = to_times

    t0 = to_times[0]
    in_secs = [(t - t0).total_seconds() for t in in_times]
    out_secs = [(t - t0).total_seconds() for t in to_times]
    for k in data:
        new_data[k] = np.interp(out_secs, in_secs, data[k])
    return new_data


def get_f107(start, end, verbose=False):
    """
    Downloads f107 data and returns f107 & f107a for time period.
    f107a is either 81-day-average (if possible) or averaged over previous 41 days
    """

    # Download f107 if it doesn't exist
    if not os.path.exists('apf107_temp.txt'):
        download_ap107_file()
    # dict w/ keys: times, f107
    f107data = read_ap107_file('apf107_temp.txt')
    # dict w/ keys: times, f107, f107a
    f107 = {}

    # Find out where our date range is
    avg_start = start - timedelta(days=41)
    avg_end = end + timedelta(days=41)
    iAvgStart = 0 # Data starts at like 1950 so we should be ok to use this
    iAvgEnd = 0
    # The dates we want data for
    iDataStart=0; iDataEnd = 0
    if verbose:
        print(f"Looking for F107 start/end: {avg_start}/{avg_end}")
    for n, t in enumerate(f107data['times']):
        if iAvgStart == 0:
            if t > avg_start:
                iAvgStart = n - 1
        elif iAvgEnd == 0:
            if iDataStart == 0:
                if t > start:
                    iDataStart = n - 1
            elif iDataEnd == 0:
                if t > end:
                    iDataEnd = n - 1
            if t > avg_end:
                iAvgEnd = n - 1
                break
    if iAvgStart == 0:
        raise ValueError("Could not find start/end times!!")
    if iAvgEnd == 0:
        print("Using a 41-day average for f107a")
        iAvgEnd = iDataStart
    f107['times'] = f107data['times'][iDataStart:iDataEnd]
    f107['f107a'] = np.zeros(len(f107['times']))
    f107['f107']  = f107data['f107'][iDataStart:iDataEnd].astype(float)

    for iIter in range(len(f107['times'])):
        f107['f107a'][iIter] = np.mean(f107data['f107'][iAvgStart+iIter:iAvgEnd+iIter]).astype(float)
    return f107


def get_imf(start, end, doGiveAE=True, verbose=False):

    if verbose:
        print("-> Downloading OMNI data using ", start, " -> ", end)
    results = download_omni_data(start, end, "-all")
    omniDirty = parse_omni_data(results)
    imf_ae = clean_omni(omniDirty)

    for v in imf_ae:
        if 'a' in v and not doGiveAE:
            continue # skip ae/au/al
        imf_ae[v] = np.array(imf_ae[v])
        t_ma = np.where((imf_ae['times'] >= start) & (imf_ae['times'] <= end))
        imf_ae[v] = imf_ae[v][t_ma]

    imf_ae['btot'] = np.sqrt(imf_ae['bx']**2 + imf_ae['by']**2 + imf_ae['bz']**2)
    imfang = np.degrees(np.atan2(imf_ae['by'], imf_ae['bz']))
    imfang = np.where(imfang<0, imfang+360, imfang) # -180-180 -> 0-360
    imf_ae['bangle'] = imfang

    return imf_ae


def calc_hp(ae):
    try:
        return 0.102*ae + 8.953
    except TypeError:
        return 0.102*np.array(ae) + 8.953


if __name__ == '__main__':
    args = get_args()
    main(args)
