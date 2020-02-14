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
ARG_LS_TRANSFER = "ls"
ARG_OUT = "output"
ARG_RENAME = "rename"
ARG_RUNNING_LOG = "hist"
ARG_TEMP_RUNNING_LOG = "hist_temp"
ARG_TRANS_BAM = "transfer_bam"
ARG_TRANS_FASTQ = "transfer_fastq"
ARG_TUMOR_BASE = "tumor"

COUNT_CASES = "_case_count"
COUNT_SAMPLES = "_sample_count"
DATE = "Date"
DATE_GS = "End"
FILE = "File"
GSCOMMAND = "gsutil -m cp -r -L "
HISTORIC_LOG_DEL = "\t"
SOURCE = "Source"
SOURCE_GS = "Source"
MD5 = "Md5"
MD5_GS = "Md5"
MD5_LOG = "Hash(MD5)"
ORIGINAL_CASE_ID = "Original-case-id"
ORIGINAL_SAMPLE_ID = "Original-sample-id"
RENAME = "rename"
RENAMED_CASE_ID = "Rename-case-id"
RENAMED_SAMPLE_ID = "Rename-sample-id"
RESULT = "Result"
RESULT_GS = "Result"
SIZE = "Size"
SIZE_GS = "Source Size"
SIZE_LOG = "Size(bytes)"
TRANSFER = "transfer"
OK = "OK"
OK_GS = "OK"

alreadytransferred = {}
historicLogHeader = [FILE,MD5_LOG,SIZE_LOG,DATE]
removefiles = [".DS_Store"]

bamType = ["bam", ".bam", "bam.bai", ".bam.bai", "bai", ".bai"]
fastqType = ["fastq.gz", ".fastq.gz", "fastq", ".fastq"]
exclusionKeys = ["counts_colon"]

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
                print("ERROR, the following file is not OK\n" + row[source])
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
                print("ERROR, the following file is not OK\n" + row[source])
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

def exclude_by_keys(fileInfo):
    """
    Exlude based on having or not having keys.
    :param fileInfo: File info with key as file name
    :return: New abridged file info
    """
    removeKeysList = []
    for fileName in fileInfo:
        for excludeKey in exclusionKeys:
            if excludeKey in fileName:
                print("WARNING:: "+fileName+" was excluded because it includes the following key. '"+excludeKey+"'.")
                removeKeysList.append(fileName)
        fileIdsDir = fileName.split("/")[get_dir_parse_index(fileName)]
        if (not "HTAPP-" in fileIdsDir) or (not "-SMP-" in fileIdsDir):
            print("WARNING:: "+fileName+" excluded for not having Keywords 'HTAPP-' or '-SMP-'")
            removeKeysList.append(fileName)
    for removeKey in set(removeKeysList):
        del fileInfo[removeKey]
    return(fileInfo)

def extract_ls_key(ls_line):
    if ls_line in [None, "", " "]:
        return ls_line
    return([ i for i in ls_line if not i == ""])

def extract_smp_id(ls_line):
    if ls_line in [None, "", " "]:
        return(ls_line)
    return(ls_line.split("/")[4].split("_")[0])

def extract_transfer_files(previousfiles, currentfiles,
                           transferFastq=False, transferBam=False):
    print("INFO::Extract transfer files.")
    removed = 0
    nottransferred = 0
    transferred = 0
    transferfiles = {}
    excludedtypes = {}
    ids = []

    transferTypes = []
    # These are the file extensions that will be candidates for transfer
    if transferFastq:
        transferTypes += fastqType
    if transferBam:
        transferTypes += bamType

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

def read_rename_info(filepath):
    readIds = {}
    with open(filepath, "r") as renameIds:
        for line in renameIds:
            key, value = line.split(",")
            readIds[key.strip()] = value.strip()
    return(readIds)

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

def rename_files(ids, fileInfo, transferBucket):
    print("RENAME FILES")
    if COUNT_CASES not in ids:
        ids[COUNT_CASES] = 0
    if COUNT_SAMPLES not in ids:
        ids[COUNT_SAMPLES] = 0
    caseCount = ids[COUNT_CASES]
    sampleCount = ids[COUNT_SAMPLES]

    for fileName in fileInfo:
        sourceFile = fileInfo[fileName][SOURCE]
        filePath, fileBase = os.path.split(sourceFile)
        fileIdsDir = sourceFile.split("/")[get_dir_parse_index(sourceFile)]
        fileIdsDir = fileIdsDir.split("_")[0].split("-")
        sampleId = "-".join(fileIdsDir[0:2])
        caseId = "-".join(fileIdsDir[2:4])

        fileInfo[fileName][ORIGINAL_SAMPLE_ID] = sampleId
        fileInfo[fileName][ORIGINAL_CASE_ID] = caseId

        if sampleId in ids:
            renamedSampleId = ids[sampleId]
        else:
            sampleCount = sampleCount + 1
            renamedSampleId = "HTA1-"+str(sampleCount)
            ids[sampleId] = renamedSampleId
            ids[COUNT_SAMPLES] = sampleCount
        if caseId in ids:
            renamedCaseId = ids[caseId]
        else:
            caseCount = caseCount + 1
            renamedCaseId = str(caseCount)
            ids[caseId] = renamedCaseId
            ids[COUNT_CASES] = caseCount
        filePrefix = renamedSampleId + "-" + renamedCaseId + "_"
        fileInfo[fileName][RENAME] = filePrefix + fileBase
        fileInfo[fileName][TRANSFER] = transferBucket + "/" +fileInfo[fileName][RENAME]
        fileInfo[fileName][RENAMED_SAMPLE_ID] = renamedSampleId
        fileInfo[fileName][RENAMED_CASE_ID] = renamedCaseId

    ids[COUNT_CASES] = caseCount
    ids[COUNT_SAMPLES] = sampleCount
    return(ids)

def make_historic_log(filename, info, previousinfo, tumor):
    if filename is None:
        print("WARNING:: Historic log was not given, starting a new one.")
        filename = "new_historic_log_"+str(tumor)+"_"+str(datetime.datetime.today().strftime("%m-%d-%Y-%H-%M-%S")+".txt")
        print("INFO:: Creating new historic log "+filename)
    # File name, hash, size, date
    output = [HISTORIC_LOG_DEL.join(historicLogHeader)]
    for data in previousinfo:
        prevfileinfo = previousinfo[data]
        output.append(HISTORIC_LOG_DEL.join([data,
                                             prevfileinfo[TRANSFER],
                                             prevfileinfo[MD5],
                                             prevfileinfo[SIZE],
                                             prevfileinfo[DATE]]))
    for data in info:
        fileinfo = info[data]
        output.append(HISTORIC_LOG_DEL.join([data,
                                             fileinfo[TRANSFER],
                                             fileinfo[MD5],
                                             fileinfo[SIZE],
                                             str(datetime.datetime.now())]))
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
        filetypes.append(get_extension(d))
        numberoffiles = numberoffiles + 1
        totalsize = totalsize + int(data[d][SIZE])
        files.append(d + " " + data[d][TRANSFER] + " " + data[d][MD5])

    filetypes = set(filetypes)
    with open(outputfile, "w") as f:
        f.writelines("Documentation for bucket transfer for the following tumor: " + tumor + "\n")
        f.writelines("Number of files transferred: " + str(numberoffiles) + "\n")
        f.writelines("Size of files: " + str(round(totalsize/1024/1024/1024,2)) + " GB ("+str(totalsize)+" bytes)\n")
        f.writelines("Types of files transferred: " + ",".join(set(filetypes)) + "\n")
        f.writelines("\n")
        f.writelines("\n".join(files))

def make_gsutil_command(outputfile, bucket, data):
    commands = []
    for info in data:
        commands.append(" ".join([GSCOMMAND,
                                  bucket + "-" + str(datetime.date.today()) + ".txt",
                                  info,
                                  data[info][TRANSFER]]))
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
                print("ERROR, the following file is not OK\n" + row[source])
                error = True
    if(error):
        exit(304)

def qc_ids(idFile, ids):
    print("INFO::Starting QC IDs")
    if idFile is None:
        return(False)

    # First exclude known malformed named (must have keys)

    # Confirm the files have key word in them
    ids = exclude_by_keys(ids)

    success = True

    referenceIds = read_reference_ids(idFile)
    returnIds = {}
    assay_count = {}

    for filename in ids:
        try:
            fileId = filename.split("/")[get_dir_parse_index(filename)]
            fileId, assay = fileId.split("_")[0:2]
            assay_count[assay] = assay_count.setdefault(assay,0) + 1
            if not fileId in referenceIds:
                print("ERROR:: The following file has an ID that does not match the expected ids.")
                print("ERROR:: "+filename)
                success = False
            else:
                returnIds[filename] = ids[filename]
        except:
            print("ERROR:: the following file is named poorly: "+str(filename))
            success = False
    print("INFO::The following assay counts were found.")
    print(os.linesep.join(["Assay: "+str(key)+"  Count: "+str(count) for key,count in assay_count.items()]))
    return({"success":success, "ids":returnIds})

def hold_ids(idFile, ids):
    print("INFO::Starting HOLD IDs")
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
                print("ID ERROR:: The following id was entered in multiple times.")
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

def read_reference_ids(fileName):
    # {(Site, Participant, Case):None}
    referenceIds = {}
    with open(fileName) as idFile:
        idreader = csv.reader(idFile, delimiter="\t")
        for row in idreader:
            key = "-".join([row[1],row[2]])
            if key in referenceIds:
                print("ID ERROR:: The following id was entered in multiple times.")
                print(str(key))
                success = False
            else:
                referenceIds[key]=None
    return(referenceIds)

def write_rename_info(ids, transfer, fileName):
    """
    Write a file that shows the mapping between each patient or each case id and it's htan pairing.
    :param ids:
    :param fileName:
    :return:
    """
    if ids is None:
        return()
    base, ext = os.path.splitext(fileName)
    keyFileName = base+"-KEY.csv"
    timeStamp = str(datetime.datetime.today().strftime("%m-%d-%Y-%H-%M-%S"))
    if os.path.exists(fileName):
        newName = base + timeStamp + ext
        shutil.move(fileName,newName)
    if os.path.exists(keyFileName):
        newName = base + timeStamp + "-KEY.csv"
        shutil.move(keyFileName,newName)
    with open(fileName,"w") as updateIds:
        content = "\n".join([",".join([str(id),str(ids[id])]) for id in ids.keys()])
        updateIds.write(content)
    with open(keyFileName, "w") as updateKeyIds:
        updateKeyIds.write("Patient Id, Case Id, HTAN Patient Id, HTAN Case Id, HTAN Full Prefix, Transferred File\n")
        content = "\n".join([",".join([transfer[fileName][ORIGINAL_SAMPLE_ID],
                                       transfer[fileName][ORIGINAL_CASE_ID],
                                       transfer[fileName][RENAMED_SAMPLE_ID].split("-")[1],
                                       transfer[fileName][RENAMED_CASE_ID],
                                       transfer[fileName][RENAMED_SAMPLE_ID]+"-"+transfer[fileName][RENAMED_CASE_ID],
                                       transfer[fileName][RENAME]]) for fileName in transfer])
        updateKeyIds.write(content)

def write_ids_keys(ids, qc_ids, fileName):
    """
    Wrtie the "key" file that shows Patient and Case ids together on the same line with the translated HTAN ids.
    :param ids:
    :param qc_ids:
    :param fileName:
    :return:
    """
    if (id_mapping is None) or (htapp_ids is None) or (fileName is None):
        print("Warning:: Did not get enough information to write the 'key' file.")
        return()
    if os.path.exists(fileName):
        base, ext = os.path.splitext(fileName)
        newName = base + str(datetime.datetime.today().strftime("%m-%d-%Y-%H-%M-%S")) + ext
        shutil.move(fileName,newName)


def args_exist(args, argsList):
    for i in argsList:
        if not i in args:
            return(False)
        if args[i] is None:
            return(False)
    return(True)

prsr = argparse.ArgumentParser(prog="Admin scripts for bucket transfer")
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
prsr_doc.add_argument("--rename", metavar=ARG_RENAME, help="Mapping file to rename files.")
prsr_doc.add_argument("--qc_ids",metavar=ARG_ID_QC, help="File ID file for QC.")
prsr_doc.add_argument("--hold_ids",metavar=ARG_ID_HOLD, help="File ID file for holding.")
prsr_doc.add_argument("--transfer_fastq",action='store_true', help="Allow Fastqs to be transferred.")
prsr_doc.add_argument("--transfer_bam",action='store_true', help="Allow bams to be transferred.")
args = prsr.parse_args()
args = dict(vars(args))

success = True

# Log the parameters
if len(args) == 0:
    print("No parameters were passed in.")
else:
    print('The following parameters were passed in:')
    for arg in args:
        print(" = ".join([arg,str(args[arg])]))

# Convert GS_logs if needed
if args_exist(args,[ARG_GSLOG_CONV, ARG_OUT, ARG_GSLOG_CONV, ARG_OUT]):
    print("STARTING\nConverting GSUTIL Logs to historic log format.")
    convert_gs_log_to_historic_log(args[ARG_GSLOG_CONV],args[ARG_OUT])
    print("ENDING: Completed with no error.")
    exit(0)

# Document and prepare the transfer
if args_exist(args,[ARG_DOCUMENT, ARG_TUMOR_BASE, ARG_BUCKET_TRANSFER,
                    ARG_LS_TRANSFER, ARG_TEMP_RUNNING_LOG, ARG_GSUTIL_CMD]):
    print("STARTING\nPreparing documentation and commands for transfer.")
    # Generate report for tumor
    previous = {}
    print(args)
    if not args[ARG_RUNNING_LOG] is None:
        previous = read_historic_log(args[ARG_RUNNING_LOG])
    else:
        print("INFO:: Skip historic log.")
    current = read_gs_ls(args[ARG_LS_TRANSFER])

    # Get the diff
    transfer = extract_transfer_files(previous,
                                      current,
                                      transferFastq=args[ARG_TRANS_FASTQ],
                                      transferBam=args[ARG_TRANS_BAM])
    #QC ids
    if (ARG_ID_QC in args) and (not args[ARG_ID_QC] is None):
        results =  qc_ids(args[ARG_ID_QC], transfer)
        success = success and results["success"]
        transfer = results["ids"]
        if success:
            print("INFO::QC ID Check passed.")
        else:
            print("ERROR::QC ID Check failed.")
    else:
        print("WARNING:: QC IDS were not checked")

    # Evaluate hold ids
    if(ARG_ID_HOLD in args) and (not args[ARG_ID_HOLD] is None):
        results = hold_ids(args[arg_ID_HOLD], transfer)
        success = success and results["success"]
        transfer = results["ids"]
        if success:
            print("INFO::Hold ID Check passed.")
        else:
            print("ERROR::Hold ID QC failed")
    else:
        print("WARNING::Hold IDS were not given.")

    # Rename files to the HTAPP Center convention
    currentRenameIds = read_rename_info(args[ARG_RENAME])
    updatedRenameIds = rename_files(currentRenameIds, transfer, args[ARG_BUCKET_TRANSFER])
    write_rename_info(updatedRenameIds,transfer, args[ARG_RENAME])

    # Make a historic log
    ## File name, Hash (md5), Size, Date
    if os.path.exists(args[ARG_TEMP_RUNNING_LOG]):
        print("ERROR in making temp historic log copy. The destination file already exists.")
        print("DESTINATION: "+args[ARG_TEMP_RUNNING_LOG])
    if not args[ARG_RUNNING_LOG] is None:
        shutil.move(args[ARG_RUNNING_LOG], args[ARG_TEMP_RUNNING_LOG])
    make_historic_log(filename=args[ARG_RUNNING_LOG], info=transfer, previousinfo=previous, tumor=args[ARG_TUMOR_BASE])

    # Make file for gsutil cp command.
    make_gsutil_command(args[ARG_GSUTIL_CMD],args[ARG_TUMOR_BASE], transfer)

    # Make documentation
    make_documentation(args[ARG_DOCUMENT], args[ARG_TUMOR_BASE], transfer)
    if success:
        print("ENDING::Completed documentation and reporting with no error.")
        exit(0)
    else:
        print("WARNING COMPLETED WITH ERROR.")
        exit(400)

# Check transfer
if args_exist(args,[ARG_CHECK_LOG]):
    print("STARTING\nChecking GSUTIL log for transfer.")
    check_gs_log_to_historic_log(args[ARG_CHECK_LOG])
    print("ENDING::Completed with no error.")
    exit(0)