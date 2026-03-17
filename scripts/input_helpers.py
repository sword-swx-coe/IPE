import json, urllib.request, os
from datetime import datetime, timedelta
import numpy as np
import requests
import re

from supermag_api import SuperMAGGetIndices


def reformat_date(date_str):
    """
    Parse a string into pythonic datetime; can include -'s and time (formatted as T00:00:00Z)
    """
    if len(date_str) == 8:
        date_str = datetime.strptime(date_str, '%Y%m%d')
    elif len(date_str) == 10:
        date_str = datetime.strptime(date_str, '%Y-%m-%d')
    elif len(date_str) == 18:
        date_str = datetime.strptime(date_str, '%Y%m%dT%H:%M:%SZ')
    elif len(date_str) == 20:
        date_str = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
    else:
        raise ValueError("date is not formatted correctly: " + date_str)
    return date_str

#############
# F107 helpers
## Taken from GITM/srcPython/f107_download.py
#############
def run_command(command, isVerbose=False):
    if (isVerbose):
        print("   -> Running Command : ")
        print("      ", command)
    os.system(command)
    return True

def download_ap107_file():

    import time

    local_file = "apf107_temp.txt"
    command = "wget"
    command = command + " -O " + local_file
    command = command + " https://chain-new.chain-project.net/echaim_downloads/apf107.dat"
    didWork = run_command(command)
    time.sleep(2) # make sure it's done downloading
    if (not didWork):
        local_file = "none"
    return local_file

def read_ap107_file(file):

    if (file == "none"):
        local_file = download_ap107_file()
    else:
        local_file = file

    if (os.path.exists(local_file)):
        times = []
        f107 = []
        print(' -> Reading file : ', local_file)
        with open(local_file, 'r') as fpin:
            for line in fpin:
                iYear = int(line[1:3])
                if (iYear > 50):
                    iYear += 1900
                else:
                    iYear += 2000
                iMonth = int(line[4:6])
                iDay = int(line[7:9])
                iF107 = float(line[39:44])
                times.append(datetime(iYear, iMonth, iDay))
                f107.append(iF107)
    else:
        raise FileNotFoundError("Can't seem to find file : " + local_file +
                                "\ndownload probably didn't work!")
    data = {'times' : np.array(times),
            'f107' : np.array(f107, dtype=float)}
    return data




#############
# Kp helpers
## The following functions were downloaded, and slightly modified, from code
## made public by GFZ Potsdam. From the link
## https://kp.gfz.de/en/data
#############

def __checkdate__(starttime,endtime):
    if starttime > endtime:
        raise NameError("Error! Start time must be before or equal to end time")
    return True

def __checkIndex__(index):
    if index not in ['Kp', 'ap', 'Ap', 'Cp', 'C9', 'Hp30', 'Hp60', 'ap30', 'ap60', 'SN', 'Fobs', 'Fadj']:
        raise IndexError("Error! Wrong index parameter! \nAllowed are only the string parameter: 'Kp', 'ap', 'Ap', 'Cp', 'C9', 'Hp30', 'Hp60', 'ap30', 'ap60', 'SN', 'Fobs', 'Fadj'")
    return True

def __checkstatus__(status):
    if status not in ['all', 'def']:
        raise IndexError("Error! Wrong option parameter! \nAllowed are only the string parameter: 'def'")
    return True

def __addstatus__(url,status):
    if status == 'def':
        url = url + '&status=def'
    return url

def get_gfz(starttime, endtime, index, status='all'):

    result_t=0; result_index=0; result_s=0
    tmp_result = {} # store data before averaging
    try:
        __checkIndex__(index)
        __checkstatus__(status)
        # We need 24-hr average of Kp so get data +/- 1 day
        start = starttime - timedelta(days=1)
        end = endtime + timedelta(days=1)
        time_string = "start=" + start.strftime('%Y-%m-%dT%H:%M:%SZ')
        time_string += "&end=" + end.strftime('%Y-%m-%dT%H:%M:%SZ')
        url = 'https://kp.gfz-potsdam.de/app/json/?' + time_string  + "&index=" + index
        if index not in ['Hp30', 'Hp60', 'ap30', 'ap60', 'Fobs', 'Fadj']:
            url = __addstatus__(url, status)

        webURL = urllib.request.urlopen(url)
        binary = webURL.read()
        text = binary.decode('utf-8')

        try:
            data = json.loads(text)
            str_times = tuple(data["datetime"])
            tmp_result['times'] = []
            for t in str_times:
                tmp_result['times'].append(reformat_date(t))
            tmp_result[index] = tuple(data[index])
            if index not in ['Hp30', 'Hp60', 'ap30', 'ap60', 'Fobs', 'Fadj']:
                result_s = tuple(data["status"])
        except:
            print(text)

    except NameError as er:
        print(er)
    except IndexError as er:
        print(er)
    except ValueError:
        print("Error! Wrong datetime string")
        print("Both dates must be the same format.")
        print("Datetime strings must be in format yyyy-mm-dd or yyyy-mm-ddTHH:MM:SSZ")
    except urllib.error.URLError:
        print("Connection Error\nCan not reach " + url)
    finally:
        # Kp has a 3-hour cadence so 8/day
        result = {}
        for v in tmp_result:
            tmp_result[v] = np.array(tmp_result[v])
        result['times'] = tmp_result['times'][8:-8]
        result[index] = tmp_result[index][8:-8]
        avg_colname = index + 'Avg'
        result[avg_colname] = np.zeros_like(result[index])
        for iTime in range(len(result['times'])):
            result[avg_colname][iTime] = np.mean(tmp_result[index][iTime:iTime+15])
        return result


#############
# IMF helpers
## Taken from GITM/srcPython/omniweb.py which
## is derived from https://omniweb.gsfc.nasa.gov/html/omni_min_data.html
#############
#inputs: dates and info desired
#date1 and date2 format example: "20110620" means June 20, 2011
def download_omni_data(date1, date2, info):

    url_i = "https://omniweb.gsfc.nasa.gov/cgi/nx1.cgi"
    params_i = "activity=retrieve&res=min&spacecraft=omni_min"
    params_i += "&start_date=" + date1.strftime("%Y%m%d")
    params_i += "&end_date=" + date2.strftime("%Y%m%d")

    if info == "-imf":
        params_i += "&vars=14&vars=17&vars=18"
    elif info == "-ae":
        params_i += "&vars=37&vars=38&vars=39"
    elif info == "-sw":
        params_i += "&vars=22&vars=23&vars=24&vars=25&vars=26"
    elif info == "-all":
        params_i += "&vars=14&vars=17&vars=18&vars=22&vars=23&vars=24&vars=25&vars=26&vars=37&vars=38&vars=39"
    else:   #if nothing is inputted for desired info
        params_i += "&vars=14&vars=17&vars=18&vars=22&vars=23&vars=24&vars=25&vars=26&vars=37&vars=38&vars=39"
    params_i += "&back="

    res = requests.get(url = url_i, params = params_i)
    return res.text     #this returns the info file from the get request

def parse_omni_data(results):

    names = {'BX, nT (GSE, GSM)' : 'bx',
             'BY, nT (GSM)' : 'by',
             'BZ, nT (GSM)' : 'bz',
             'Vx Velocity,km/s' : 'vx',
             'Vy Velocity, km/s' : 'vy',
             'Vz Velocity, km/s' : 'vz',
             'Proton Density, n/cc' : 'n',
             'Temperature, K' : 't',
             'Proton Temperature, K' : 't',
             'AE-index, nT' : 'ae',
             'AL-index, nT' : 'al',
             'AU-index, nT' : 'au'}

    lines = results.splitlines()

    IsFound = 0
    iLine = 0
    while (not IsFound):
        line = lines[iLine]
        m = re.match(r'<B>.*',line)
        if m:
            IsFound = 1
        iLine += 1

    data = {}
    data["Vars"] = []
    data["nVars"] = 0
    data["times"] = []

    IsFound = 0
    while (not IsFound):
        line = lines[iLine]
        if (len(line) < 2):
            IsFound = 1
        else:
            v = names[line[3:]]
            data["Vars"].append(v)
            data[v] = []
            data["nVars"] += 1
        iLine += 1

    # Skip over YYYY line:
    iLine += 1

    nV = data["nVars"] + 4
    IsFound = 0
    while (not IsFound):
        aline = lines[iLine].split()
        if (len(aline) < nV):
            IsFound = 1
        else:
            year = int(aline[0])
            doy = int(aline[1])-1
            hour = int(aline[2])
            minute = int(aline[3])
            base = datetime(year,1,1,hour,minute,0)
            actual = base + timedelta(days=doy)
            data["times"].append(actual)
            for i,v in enumerate(data["Vars"]):
                data[v].append(float(aline[i + 4]))
        iLine += 1

    return data

def clean_omni(data):

    newdata = {"times" : [],
               "bx" : [],
               "by" : [],
               "bz" : [],
               "vx" : [],
               "vy" : [],
               "vz" : [],
               "n" : [],
               "t" : [],
               "ae" : [],
               "au" : [],
               "al" : []}

    i = 0
    while (np.abs(data["vx"][i]) > 10000.0):
        i += 1

    vx0 = data["vx"][i]
    vy0 = data["vy"][i]
    vz0 = data["vz"][i]
    n0 = data["n"][i]
    temp0 = data["t"][i]

    for i, t in enumerate(data["times"]):
        bx = data["bx"][i]
        by = data["by"][i]
        bz = data["bz"][i]
        vx = data["vx"][i]
        vy = data["vy"][i]
        vz = data["vz"][i]
        n = data["n"][i]
        temp = data["t"][i]

        if (np.abs(vx) > 10000):
            vx = vx0
            vy = vy0
            vz = vz0
            n = n0
            temp = temp0
        else:
            vx0 = vx
            vy0 = vy
            vz0 = vz
            n0 = n
            temp0 = temp

        if (np.abs(bx) < 1000):
            newdata["times"].append(t)
            newdata["bx"].append(bx)
            newdata["by"].append(by)
            newdata["bz"].append(bz)
            newdata["vx"].append(vx)
            newdata["vy"].append(vy)
            newdata["vz"].append(vz)
            newdata["n"].append(n)
            newdata["t"].append(temp)
            newdata["ae"].append(data["ae"][i])
            newdata["au"].append(data["au"][i])
            newdata["al"].append(data["al"][i])

    return newdata


def write_swmf_imf_file(data, fileout,
                        message = 'output from write_swmf_imf_file\n'):

    print(f"Writing IMF file: '{fileout}'")
    fp = open(fileout, 'wb')

    fp.write("\n".encode())
    fp.write(message.encode())
    fp.write("\n".encode())
    fp.write("No AlphaRatio was considered\n".encode())
    fp.write("\n".encode())
    fp.write("#TIMEDELAY\n".encode())
    fp.write("0.0\n".encode())
    fp.write("\n".encode())
    fp.write("#START\n".encode())

    i = 0
    while (np.abs(data["vx"][i]) > 10000.0):
        i += 1

    vx0 = data["vx"][i]
    vy0 = data["vy"][i]
    vz0 = data["vz"][i]
    n0 = data["n"][i]
    temp0 = data["t"][i]

    for i, t in enumerate(data["times"]):
        bx = data["bx"][i]
        by = data["by"][i]
        bz = data["bz"][i]
        vx = data["vx"][i]
        vy = data["vy"][i]
        vz = data["vz"][i]
        n = data["n"][i]
        temp = data["t"][i]

        if (np.abs(vx) > 10000):
            vx = vx0
            vy = vy0
            vz = vz0
            n = n0
            temp = temp0
        else:
            vx0 = vx
            vy0 = vy
            vz0 = vz
            n0 = n
            temp0 = temp

        if (np.abs(bx) < 1000):
            sTime = t.strftime(' %Y %m %d %H %M %S 000')
            sImf = "%8.2f %8.2f %8.2f" % (bx, by, bz)
            sSWV = "%9.2f %9.2f %9.2f" % (vx, vy, vz)
            sSWnt = "%8.2f %11.1f" % (n, temp)

        line = sTime + sImf + sSWV + sSWnt + "\n"

        fp.write(line.encode())

    fp.close()


#############
# AE/SME helpers
## Taken from GITM/srcPython/
#############

def write_sme_file(data, fileout, message = "none"):

    print(f"Writing AE file: '{fileout}'")

    l0 = 'File created by python code using write_sme_file\n'
    l1 = '============================================================\n'
    l2 = '<year>  <month>  <day>  <hour>  <min>  <sec>  '
    l2 = l2 + '<SME (nT)>  <SML (nT)>  <SMU (nT)>\n'

    fp = open(fileout, 'wb')
    fp.write(l0.encode())
    fp.write("\n".encode())
    if (message != "none"):
        m = message + "\n"
        fp.write(m.encode())
    fp.write(l1.encode())
    fp.write(l2.encode())

    for i, t in enumerate(data['times']):
        ae = data['ae'][i]
        al = data['al'][i]
        au = data['au'][i]
        out = " %8.2f %8.2f %8.2f" % (ae, al, au)
        ymdhms = t.strftime('%Y  %m  %d  %H  %M  %S')
        line = ymdhms + out + "\n"
        fp.write(line.encode())

    fp.close()

    return fileout


def download_sme_data(start, end):

    length = (end - start).total_seconds()

    if (length < 60):
        print('Length requested: ', length)
        print('This is too short. Stopping in download_sme_data')
        exit()

    if (length > 31.0*86400.0):
        print('Length requested: ', length)
        print('This is too long. Stopping in download_sme_data')
        exit()

    print('--> Downloading SME data')
    userid = 'ridley'
    (status,idxdata) = SuperMAGGetIndices(userid, start, length, 'all')
    try:
        print(f"Found {len(idxdata['tval'])} times")
    except:
        raise ConnectionError("Could not connect to SuperMag")

    sme_data = {'ae':[], 'au':[], 'al':[]}
    times = []
    base = datetime(1970,1,1,0,0,0)
    for i, dt in enumerate(idxdata['tval']):
        times.append(base + timedelta(seconds=dt))
        sme_data['ae'].append(idxdata['SME'][i])
        sme_data['au'].append(idxdata['SMU'][i])
        sme_data['al'].append(idxdata['SML'][i])
    sme_data['times'] = times

    return sme_data
