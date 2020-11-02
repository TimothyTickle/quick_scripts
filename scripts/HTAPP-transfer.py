#!/usr/bin/env python3

import argparse
import csv
import datetime
import os
import shutil

ARG_BUCKET_TRANSFER = "bucket"
ARG_CHECK_LOG = "check"
ARG_DOCUMENT = "document_out"
ARG_GSLOG_CONV = "log2hist"
ARG_GSUTIL_CMD = "cmd_out"
ARG_ID_QC = "qc_ids"
ARG_ID_HOLD = "hold_ids"
ARG_ID_MAP = "map_ids"
ARG_LS_TRANSFER = "ls"
ARG_OUT = "output"
ARG_RENAME = "rename"
ARG_RUNNING_LOG = "hist"
ARG_TEMP_RUNNING_LOG = "hist_temp"
ARG_TRANS_BAM = "transfer_bam"
ARG_TRANS_FASTQ = "transfer_fastq"
ARG_TUMOR_BASE = "tumor"

DATE = "Date"
DATE_GS = "End"
FILE = "File"
GSCOMMAND = "gsutil -m cp -r -L "
HISTORIC_LOG_DEL = "\t"
HTAPP_PILOT_PROJECT = "HTA1"
ID_TOP_COUNT = "MAX_ID"
SOURCE = "Source"
SOURCE_GS = "Source"
MD5 = "Md5"
MD5_GS = "Md5"
MD5_LOG = "Hash(MD5)"
RESULT = "Result"
RESULT_GS = "Result"
SIZE = "Size"
SIZE_GS = "Source Size"
SIZE_LOG = "Size(bytes)"
OK = "OK"
OK_GS = "OK"

alreadytransferred = {}
historicLogHeader = [FILE,MD5_LOG,SIZE_LOG,DATE]
removefiles = [".DS_Store"]

bamType = ["bam","bai","bam.bai"]
fastqType = ["fastq.gz", "fastq"]

def check_gs_log(logfile):
    read_gs_log(logfile)

def convert_gs_log_to_historic_log(logfile, newfile):
    convertinfo = {}
    with open(logfile) as logFile:
        source, md5, size, dateinfo, result = -1,-1,-1,-1,-1
        logreader = csv.reader(logFile, delimiter=",")
        for row in logreader:
            if source == -1:
                source = row.index(SOURCE_GS)
                md5 = row.index(MD5_GS)
                size = row.index(SIZE_GS)
                dateinfo = row.index(DATE_GS)
                result = row.index(RESULT_GS)
                continue

            # Flag things that were not ok.
            if not row[result] ==  OK:
                print("ERROR:: ERROR, the following file is not OK\n" + row[source])
                exit(303)

            convertinfo[row[source]] = {SOURCE:row[source], MD5:row[md5], SIZE:row[size], DATE:row[dateinfo]}
    with open(newfile, "w") as f:
        f.write(HISTORIC_LOG_DEL.join(historicLogHeader)+"\n")
    with open(newfile, "a") as f:
        logwriter = csv.DictWriter(f,fieldnames=[SOURCE,MD5,SIZE,DATE], delimiter=HISTORIC_LOG_DEL)
        for fileinfo in convertinfo:
            logwriter.writerow(convertinfo[fileinfo])

def read_gs_log(logfile):
    error = False
    source, md5, result = -1,-1,-1
    # Read log
    with open(logfile) as logFile:
        logreader = csv.reader(logFile, delimiter=",")
        for row in logreader:
            if source == -1:
                source = row.index(SOURCE_GS)
                md5 = row.index(MD5_GS)
                result = row.index(RESULT_GS)
                continue

            # Flag things that were not ok.
            if not row[result] ==  OK:
                print("ERROR:: ERROR, the following file is not OK\n" + row[source])
                error = True

            alreadytransferred[row[source]] = {SOURCE:row[source], MD5:row[md5]}
    if error: exit(301)
    return(alreadytransferred)

def read_gs_ls(lsfile):
    print("INFO:: Read GS LS")
    print("INFO:: GS LS file "+str(lsfile))
    filestart = "gs://"
    dirchar = "/:"
    hashkey = 'Hash'
    mdkey = "(md5):"
    fileinfo = {}
    with open(lsfile) as lsFile:
        lsreader = csv.reader(lsFile, delimiter=" ")
        for row in lsreader:
            if len(row) == 0:
                continue
            # Check if is a file but skip dir
            if (row[0][0:5] == filestart) and (not row[0][-2:] == dirchar):
                filename = row[0]
                filename = filename[:-1] if filename[-1] == ":" else filename
                lsline = next(lsreader)
                lslineinfo = {}
                while(not lsline[0][0:4] == "ACL:"):
                    keys = extract_ls_key(lsline)
                    if len(keys) > 2:
                        keys[0] = " ".join(keys[0:2])
                    lslineinfo[keys[0]] = keys[-1]
                    lsline = [ i for i in next(lsreader) if not i == ""]
                fileinfo[filename] = {SOURCE: filename,
                                      MD5: lslineinfo["Hash (md5):"],
                                      SIZE: lslineinfo["Content-Length:"]}
    return(fileinfo)

def extract_ls_key(ls_line):
    if ls_line in [None, "", " "]:
        return ls_line
    return([ i for i in ls_line if not i == ""])

def extract_smp_id(ls_line):
    if ls_line in [None, "", " "]:
        return(ls_line)
    return(ls_line.split("/")[4].split("_")[0])

def extract_transfer_files(previousfiles, currentfiles, transferTypes=[]):
    print("INFO::Extract transfer files.")
    removed = 0
    nottransferred = 0
    transferred = 0
    transferfiles = {}
    excludedtypes = {}
    ids = []

    for currentfile in currentfiles:

        # Remove specific files
        if os.path.basename(currentfile) in removefiles:
            print("Not transferring::" + currentfile)
            removed = removed + 1
            continue

        # Only send files in the transfer types
        ext = get_extension(currentfile)
        if not ext in transferTypes:
            excludedtypes[ext] = excludedtypes.setdefault(ext,0)+1
            continue

        # Keep files that should be transferred
        ## If the files has not been transferred, transfer
        if not currentfile in previousfiles:
            transferfiles[currentfile] = currentfiles[currentfile]
            transferred = transferred + 1
            ids.append(extract_smp_id(currentfile))
        else:
            ## If the file has a different hash, transfer
            currenthash = currentfiles[currentfile][MD5]
            previoushash = previousfiles[currentfile][MD5]

            if not currenthash == previoushash:
                transferfiles[currentfile] = currentfiles[currentfile]
                transferred = transferred + 1
                ids.append(extract_smp_id(currentfile))
            else:
                nottransferred = nottransferred + 1

    ids = list(set(ids))
    ids.sort()
    print("INFO:: Number of files to transfer = "+str(transferred))
    print("INFO:: Number of files already transferred previously = "+str(len(previousfiles)))
    print("INFO:: Number of sample ids to be transferred = " + str(len(ids)))
    for type, count in excludedtypes.items():
        print('WARNING:: The following file type was found and ignored '+str(count)+' many times: '+ type)
    print("\n".join(["Sample ids to be transferred:"] + ids))
    return(transferfiles)

def get_extension(filepath):
    if filepath is None:
        return(None)
    filepath = filepath.split("/")[-1]
    path_elements = filepath.split(".")
    if len(path_elements) in [0,1]:
        return("")
    if len(path_elements) > 1:
        if(path_elements[-1] == "log"):
            return("log")
        return(".".join(path_elements[1:]))

def get_dir_parse_index(filepath):
    ext = get_extension(filepath)
    if ext in bamType:
        return(5)
    return(4)

def read_historic_log(hisfile):
    convertinfo = {}
    with open(hisfile) as logFile:
        file, md5, size, dateinfo = -1,-1,-1,-1
        logreader = csv.reader(logFile, delimiter=HISTORIC_LOG_DEL)
        for row in logreader:
            if file == -1:
                file = row.index(FILE)
                md5 = row.index(MD5_LOG)
                size = row.index(SIZE_LOG)
                dateinfo = row.index(DATE)
                continue
            convertinfo[row[file]] = {SOURCE:row[file], MD5:row[md5], SIZE:row[size], DATE:row[dateinfo]}
    return(convertinfo)

def make_historic_log(filename, info, previousinfo, tumor):
    if filename is None:
        print("WARNING:: Historic log was not given, starting a new one.")
        filename = "new_historic_log_"+str(tumor)+"_"+str(datetime.datetime.today().strftime("%m-%d-%Y-%H-%M-%S")+".txt")
        print("INFO:: Creating new historic log "+filename)
    # File name, hash, size, date
    output = [HISTORIC_LOG_DEL.join(historicLogHeader)]
    for data in previousinfo:
        prevfileinfo = previousinfo[data]
        output.append(HISTORIC_LOG_DEL.join([prevfileinfo[SOURCE], prevfileinfo[MD5],
                                             prevfileinfo[SIZE], prevfileinfo[DATE]]))
    for data in info:
        fileinfo = info[data]
        output.append(HISTORIC_LOG_DEL.join([fileinfo[SOURCE],fileinfo[MD5],fileinfo[SIZE],str(datetime.datetime.now())]))
    with open(filename, "a") as f:
        f.writelines(os.linesep.join(output))

def make_documentation(outputfile, tumor, data):
    ## Type of files
    ## Number files
    ## Total size
    ## Specific files
    filetypes = []
    numberoffiles = 0
    totalsize = 0
    files = []
    for d in data:
        # If IDs can not be extracted, then do not document
        if not split_file_to_id_tokens(os.path.split(d)[-1]) is None:
            filetypes.append(get_extension(d))
            numberoffiles = numberoffiles + 1
            totalsize = totalsize + int(data[d][SIZE])
            files.append(d + " " + data[d][MD5])

    filetypes = set(filetypes)
    with open(outputfile, "w") as f:
        f.writelines("Documentation for HTAPP transfer for the following tumor: " + tumor + "\n")
        f.writelines("Number of files transferred: " + str(numberoffiles) + "\n")
        f.writelines("Size of files: " + str(round(totalsize/1024/1024/1024,2)) + " GB ("+str(totalsize)+" bytes)\n")
        f.writelines("Types of files transferred: " + ",".join(set(filetypes)) + "\n")
        f.writelines("\n")
        f.writelines("\n".join(files))

def make_gsutil_command(outputfile, bucket, transferbucket, data, file_ids):
    commands = []
    for info in data:
        ## Info is the file name
        file_tokens = info.split("/")
        file_name = file_tokens[-1]

        add_id_to_htan_id_map(file_name=file_name,
                                      id_map=file_ids)

        updated_file_name=convert_file_name_to_htan_standard(file_name,file_ids)
        if not updated_file_name:
            print("Warning:: Skipping file for transfer.")
            print("Warning:: File Name: "+str(file_name))
            continue
        updated_file_name = transferbucket+"/"+updated_file_name
        commands.append(" ".join([GSCOMMAND,bucket + "-" + str(datetime.date.today()) + ".txt",info,updated_file_name]))
    with open(outputfile, "w") as f:
        f.writelines(os.linesep.join(commands))

def check_gs_log_to_historic_log(logfile):
    error = False
    with open(logfile) as logFile:
        result = -1,-1,-1,-1,-1
        logreader = csv.reader(logFile, delimiter=",")
        for row in logreader:
            if source == -1:
                source = row.index(SOURCE_GS)
                result = row.index(RESULT_GS)
                continue

            # Flag things that were not ok.
            if not row[result] ==  OK:
                print("ERROR:: ERROR, the following file is not OK\n" + row[source])
                error = True
    if(error):
        exit(304)

def qc_ids(idFile, ids):
    print("INFO:: Starting QC IDs")
    if idFile is None:
        return(False)

    success = True

    referenceIds = {}
    returnIds = {}
    assay_count = {}
    # {(Site, Participant, Case):None}
    with open(idFile) as idFile:
        idreader = csv.reader(idFile, delimiter="\t")
        for row in idreader:
            key = "-".join([row[1],row[2]])
            if key in referenceIds:
                print("ID ERROR:: The following id was entered in multiple times.")
                print(str(key))
                success = False
            else:
                referenceIds[key]=None
    for filename in ids:
#        try:
        parseIndex = get_dir_parse_index(filename)
        fileId = filename.split("/")[parseIndex]
        fileId, assay = fileId.split("_")[0:2]
        assay_count[assay] = assay_count.setdefault(assay,0) + 1
        if not fileId in referenceIds:
            print("ERROR:: The following file has an ID that does not match the expected ids.")
            print("ERROR:: "+filename)
            success = False
        else:
            returnIds[filename] = ids[filename]
#        except:
#            print("ERROR:: the following file is named poorly: "+str(filename))
#            success = False
    print("INFO:: The following assay counts were found.")
    print(os.linesep.join(["Assay: "+str(key)+"  Count: "+str(count) for key,count in assay_count.items()]))
    return({"success":success, "ids":returnIds})

def hold_ids(idFile, ids):
    print("INFO:: Starting HOLD IDs")
    if idFile is None:
        return(False)

    success = True

    holdIds = {}
    returnIds = {}
    assay_count = {}
    # {(Site, Participant, Case):None}
    with open(idFile) as idFile:
        idreader = csv.reader(idFile, delimiter="\t")
        for row in idreader:
            key = "-".join([row[1],row[2]])
            if key in holdIds:
                print("ERROR:: ID ERROR:: The following id was entered in multiple times.")
                print(str(key))
                success = False
            else:
                holdIds[key]=None
    for filename in ids:
        try:
            fileId = filename.split("/")[4]
            fileId, assay = fileId.split("_")
            assay_count[assay] = assay_count.setdefault(assay,0) + 1
            if fileId in holdIds:
                print("INFO:: The following file has an ID that is being held, it should not be transferred.")
                print("INFO:: "+filename)
            else:
                returnIds[filename] = ids[filename]
        except:
            print("ERROR:: the following file is named poorly: "+str(filename))
            success = False
    return({"success":success, "ids":returnIds})


def split_file_to_id_tokens(file_name):
    """
    Split a file name to the htapp and smp tokens
    :param file_name: File name to tokenize
    :return: Array ["htapp", id_number, "smp", id_number]
    """

    # Fail empty values
    if file_name is None or file_name.strip() == "":
        return None

    # Example file name
    # HTAPP-272-SMP-4831_none_channel1_S1_L003_I1_001.fastq.gz
    file_tokens = file_name.split("_")
    if len(file_tokens) < 2:
        print("ERROR:: Expected to more than 1 tokens at this step but did not.")
        print(file_tokens)
        print(file_name)
        return None
    file_tokens = file_tokens[0].split("-")
    if len(file_tokens) != 4:
        print("ERROR:: Expected to have 4 tokens at this step but did not.")
        print(file_tokens)
        print(file_name)
        return None
    if file_tokens[0] != "HTAPP" or file_tokens[2] != "SMP":
        print("ERROR:: Failed token check, the first token was expect to be 'HTAPP' and the third 'SMP'.")
        print(file_tokens)
        print(file_name)
        return None
    return(file_tokens)


def add_id_to_htan_id_map(file_name, id_map = {}):
    """
    This takes standard names with internal case and sample ids and adds them to a map
    to connect them to a HTAPP DCC standard file name
    :return:
    """

    # Ignore empty values
    if file_name is None or file_name.strip() == "":
        return True

    file_tokens = split_file_to_id_tokens(file_name)
    if file_tokens is None:
        print("WARNING:: Skipped file, could not extract ID.")
        print("WARNING:: File name: "+str(file_name))
        return False

    htapp_id = file_tokens[0] + "-" + file_tokens[1]
    smp_id = file_tokens[2] + "-" + file_tokens[3]

    if htapp_id not in id_map:
        new_htapp_id = id_map.get(ID_TOP_COUNT, 0) + 1
        if new_htapp_id in id_map.values():
            print("ERROR:: Tried to insert a duplicate HTAPP id.")
            print("ERROR:: ID "+str(new_htapp_id))
            print("ERROR:: Map="+str(id_map))
            return False
        else:
            id_map[htapp_id]=new_htapp_id
            id_map[ID_TOP_COUNT]=new_htapp_id
    if smp_id not in id_map:
        new_SMP_id = id_map.get(ID_TOP_COUNT, 0) + 1
        if new_SMP_id in id_map.values():
            print("ERROR:: Tried to insert a duplicate SMO id.")
            print("ERROR:: ID "+str(new_SMP_id))
            print("ERROR:: Map="+str(id_map))
            return False
        else:
            id_map[smp_id]=new_SMP_id
            id_map[ID_TOP_COUNT]=new_SMP_id
    return True


def convert_file_name_to_htan_standard(file_name, id_map):
    """
    Take a file  name and update it to th htan standard
    :param file_name: File name (just the file name no directory path)
    :return: new file name that is HTAN DCC compliant.
    """

    # Fail empty values
    if file_name is None or file_name.strip() == "":
        return False

    tokens = split_file_to_id_tokens(file_name)
    if not tokens is None:
        htan_prefix = HTAPP_PILOT_PROJECT+"_" +str(id_map[tokens[0]+"-"+tokens[1]])+"_"+str(id_map[tokens[2]+"-"+tokens[3]])
        return htan_prefix+"_"+file_name
    return None


def read_map_file(map_file_name):
    """
    Read in the map file
    :param map_file_name:  File path
    :return: dict of mapping
    """

    map_file = {}

    if map_file_name is None or map_file_name.strip() == "":
        return None
    if not os.path.exists(map_file_name):
        print("INFO:: The mapping file does not exist. Starting a new one.")
        print("INFO:: Generating IDS new with no history of previous assignments.")
        return map_file

    with open(map_file_name) as map_file_reader:
        for line in map_file_reader:
            if line is None or line.strip() == "":
                continue
            tokens = line.split("\t")
            tokens = [token.strip("\t\r\n ") for token in tokens]
            map_file[tokens[0]]= tokens[1]
    return map_file

def write_map_file(map_file_name, map_ids):
    """
    Write ids to file
    :param map_file_name: File to write to
    :param map_ids: Mapped ids {HTAPP_id=HTAN_DCC id}
    :return: boolean (True is success)
    """
    print('Writing Map File: map_file_name='+str(map_file_name))
    if map_file_name is None or map_file_name.strip() == "":
        return False

    if os.path.exists(map_file_name):
        map_base, map_ext = os.path.splitext(map_file_name)
        safe_name = map_base+"-"+str(datetime.datetime.today().strftime("%m-%d-%Y-%H-%M-%S"))+map_ext
        shutil.move(map_file_name, safe_name)

    with open(map_file_name,"w") as map_file:
        for htapp_id in map_ids:
            map_file.writelines(str(htapp_id)+"\t"+str(map_ids[htapp_id])+"\n")
    return True


def args_exist(args, argsList):
    for i in argsList:
        if not i in args:
            return(False)
        if args[i] is None:
            return(False)
    return(True)

prsr = argparse.ArgumentParser(prog="Admin scripts for HTAPP transfer")
subprsr = prsr.add_subparsers(help="Subparser")

prsr_cnv = subprsr.add_parser("convert", help="Convert file formats")
prsr_cnv.add_argument("--log2hist", metavar=ARG_GSLOG_CONV, help="Gsutil log to convert to a historic log.")
prsr_cnv.add_argument("--output", metavar=ARG_OUT, help="Output historic file name.")

prsr_check = subprsr.add_parser("check", help="Check gsutil logs after transfer.")
prsr_check.add_argument("--check", metavar=ARG_CHECK_LOG, help="GSUTIL log to check.")

prsr_doc = subprsr.add_parser("document", help="Generate documentation for transfer.")
prsr_doc.add_argument("--bucket", metavar=ARG_BUCKET_TRANSFER, help="Bucket to transfer the files to.")
prsr_doc.add_argument("--cmd_out", metavar=ARG_GSUTIL_CMD, help="GSUTIL commands output file.")
prsr_doc.add_argument("--hist", metavar=ARG_RUNNING_LOG, help="Historic running log, this will be copied, stored, then updated.")
prsr_doc.add_argument("--hist_temp", metavar=ARG_TEMP_RUNNING_LOG, help="The copy of the historic running log before it is manipulated.")
prsr_doc.add_argument("--ls", metavar=ARG_LS_TRANSFER, help="Time stamped LS for data transfer.")
prsr_doc.add_argument("--tumor", metavar=ARG_TUMOR_BASE, help="Tumor being documented.")
prsr_doc.add_argument("--document_out", metavar=ARG_DOCUMENT, help="Document file name.")
prsr_doc.add_argument("--qc_ids",metavar=ARG_ID_QC, help="HTAPP ID file for QC.")
prsr_doc.add_argument("--hold_ids",metavar=ARG_ID_HOLD, help="HTAPP ID file for holding.")
prsr_doc.add_argument("--map_ids",metavar=ARG_ID_MAP, required=True, help="Mapping file for the HTAN DCC to HTAPP/SMP ID mappings.")
prsr_doc.add_argument("--rename", metavar=ARG_RENAME, help="Output file logging the id mapping that occurred.")
prsr_doc.add_argument("--transfer_fastq",metavar=ARG_TRANS_FASTQ, help="Allow Fastqs to be transferred.")
prsr_doc.add_argument("--transfer_bam",metavar=ARG_TRANS_BAM, help="Allow bams to be transferred.")
args = prsr.parse_args()
args = dict(vars(args))

success = True

# Log the parameters
if len(args) == 0:
    print("INFO:: No parameters were passed in.")
else:
    print('INFO:: The following parameters were passed in:')
    for arg in args:
        print(" = ".join([arg,str(args[arg])]))

# Read map from file
file_ids_map = {}
if args_exist(args,[ARG_ID_MAP]):
    file_ids_map = read_map_file(args[ARG_ID_MAP])

# Convert GS_logs if needed
if args_exist(args,[ARG_GSLOG_CONV, ARG_OUT, ARG_GSLOG_CONV, ARG_OUT]):
    print("STARTING\nConverting GSUTIL Logs to historic log format.")
    convert_gs_log_to_historic_log(args[ARG_GSLOG_CONV],args[ARG_OUT])
    print("INFO:: ENDING: Completed with no error.")
    exit(0)
else:
    print("INFO:: Did not convert GSUTIL Logs to historic logs.")

# Document and prepare the transfer
if args_exist(args,[ARG_DOCUMENT, ARG_TUMOR_BASE, ARG_BUCKET_TRANSFER,
                    ARG_LS_TRANSFER, ARG_TEMP_RUNNING_LOG, ARG_GSUTIL_CMD]):
    print("STARTING\nPreparing documentation and commands for transfer.")
    # Generate report for tumor
    previous = {}
    if not args[ARG_RUNNING_LOG] is None:
        previous = read_historic_log(args[ARG_RUNNING_LOG])
    else:
        print("INFO:: Skip historic log.")
    current = read_gs_ls(args[ARG_LS_TRANSFER])

    # Get the diff
    transferExtensions = []
    if args[ARG_TRANS_FASTQ]== "YES":
        transferExtensions.extend(fastqType)
    if args[ARG_TRANS_BAM] == "YES":
        transferExtensions.extend(bamType)
    transfer = extract_transfer_files(previous,current,transferExtensions)
    #QC ids
    if (ARG_ID_QC in args) and (not args[ARG_ID_QC] is None):
        results =  qc_ids(args[ARG_ID_QC], transfer)
        success = success and results["success"]
        transfer = results["ids"]
        if success:
            print("INFO:: QC ID Check passed.")
        else:
            print("ERROR:: QC ID Check failed.")
    else:
        print("WARNING:: QC IDS were not checked")

    # Evaluate hold ids
    if(ARG_ID_HOLD in args) and (not args[ARG_ID_HOLD] is None):
        results = hold_ids(args[arg_ID_HOLD], transfer)
        success = success and results["success"]
        transfer = results["ids"]
        if success:
            print("INFO:: Hold ID Check passed.")
        else:
            print("ERROR:: Hold ID QC failed")
    else:
        print("WARNING:: Hold IDS were not given.")

    # Make a historic log
    ## File name, Hash (md5), Size, Date
    if os.path.exists(args[ARG_TEMP_RUNNING_LOG]):
        print("ERROR:: ERROR in making temp historic log copy. The destination file already exists.")
        print("ERROR:: DESTINATION: "+args[ARG_TEMP_RUNNING_LOG])
    if not args[ARG_RUNNING_LOG] is None:
        shutil.move(args[ARG_RUNNING_LOG], args[ARG_TEMP_RUNNING_LOG])
    make_historic_log(filename=args[ARG_RUNNING_LOG],
                      info=transfer,
                      previousinfo=previous,
                      tumor=args[ARG_TUMOR_BASE])

    # Make file for gsutil cp command
    make_gsutil_command(outputfile=args[ARG_GSUTIL_CMD],
                        bucket=args[ARG_TUMOR_BASE],
                        transferbucket=args[ARG_BUCKET_TRANSFER],
                        data=transfer,
                        file_ids=file_ids_map)

    # Write mapped id to file
    write_map_file(map_file_name=args[ARG_ID_MAP], map_ids=file_ids_map)

    # Make documentation
    make_documentation(args[ARG_DOCUMENT], args[ARG_TUMOR_BASE], transfer)
    if success:
        print("ENDING:: Completed documentation and reporting with no error.")
        exit(0)
    else:
        print("WARNING:: COMPLETED WITH ERROR.")
        exit(400)
else:
    print("INFO:: Did not prepare documentation.")

# Check transfer
if args_exist(args,[ARG_CHECK_LOG]):
    print("STARTING\nChecking GSUTIL log for transfer.")
    check_gs_log_to_historic_log(args[ARG_CHECK_LOG])
    print("ENDING::Completed with no error.")
    exit(0)
else:
    print("INFO:: Did not check GSUTIL log for transfer.")
