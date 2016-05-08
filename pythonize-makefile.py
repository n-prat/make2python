
# no multiple output per line e.g "out1 out2 ... : dep"

import platform
import os
import sys
import glob

try:
    path = sys.argv[1]
    directory, filename = os.path.split(path)
    print("With :", directory, filename)
except IndexError:
    print("1 argument required")
    exit(1)

# get variable dependencies
def dependsOn(linestring):
    splitted = linestring.split(" ")
    vardelimiters = ['$', '(', ')']
    dependslist = []
    for token in splitted:
        if all(delim in token for delim in vardelimiters):
            startidx = token.index("(")
            endidx = token.index(")")
            varname = token[startidx+1:endidx]
            if varname not in dependslist:
                dependslist.append(varname)

    return dependslist

# check if we need another mapping pass
def canBeComputed(dependslist, map):
    try:
        for val in dependslist:
            test = varmap[val]
        return True
    except KeyError:
        print("can NOT Computed\n\n")
        return False

# return occurences'indexes of an elemnt in a list
def indices(lst, element):
    result = []
    offset = -1
    while True:
        try:
            offset = lst.index(element, offset+1)
        except ValueError:
            return result
        result.append(offset)

def findFirstGreaterThanValueInList(val, lst):
    for i in lst:
        if i > val:
            return i
    return -1

with open(path, "r") as makefile:
    makecontent = makefile.read()
    makelines = makecontent.split("\n")
    # print(makecontent)

    # get the full list of variables e.g $(VAR1)
    vartomap = []
    fullytokenized = makecontent.split(" ")
    vardelimiters = ['$', '(', ')']
    for token in fullytokenized:
        if all(delim in token for delim in vardelimiters):
            startidx = token.index("(")
            endidx = token.index(")")
            varname = token[startidx+1:endidx]
            if not varname in vartomap:
                vartomap.append(varname)
    # print(vartomap, len(vartomap))

    # store the lines containing "="
    definelines = []
    dependslines = []
    wildcardslines = []
    for line in makelines:
        if line.find('#') == 0:
            continue
        if "=" in line and "$" not in line:
            # standard defines eg "VAR = VALUE"
            definelines.append(line)
            continue
        if "=" in line and ":" in line:
            if "wildcard" in line:
                # probably a wildcard
                print("WILDCARD found :", line)
                wildcardslines.append(line)
            continue
        if "=" in line and "$" in line and ":" not in line:
            # depends eg "VAR = $(SOMEVAR)..."
            dependslines.append(line)
            continue
    print("definelines :", definelines)
    print("dependslines :", dependslines)
    print("wildcardslines :", wildcardslines)

    # map non-dependent variables
    varmap = {}
    for line in definelines:
        splitted = line.split(" ")
        try:
            # standard defines eg "VAR = VALUE"
            idx = splitted.index("=")
            # print("definelines :", line)
            varmap[splitted[0]] = " ".join(splitted[idx + 1:])
        except ValueError:
            # probably a wildcard
            print("WILDCARD found :", line)
    print("varmap :", varmap)

    # # take care of the wildcards
    # for wild in wildcardslines:
    #     os.chdir("/mydir")
    #     for file in glob.glob("*.txt"):
    #         print(file)

    # map dependent variables
    tomaplater = [] # if depends on dependent vars
    for line in dependslines:
        splitted = line.split(" ")
        idx = splitted.index("=")
        deplist = dependsOn(line)
        print(splitted[0], "dependsOn :", deplist)
        if canBeComputed(deplist, varmap):
            # we have everything needed
            value = []
            for token in splitted[idx+1:]:
                if "$" in token:
                    startidx = token.index("(")
                    endidx = token.index(")")
                    tempname = token[startidx+1:endidx]
                    expended = token.replace("$("+tempname+")", varmap[tempname])
                    value.append(expended)
                else:
                    value.append(token)
            # value contains the full expended string
            varmap[splitted[0]] = " ".join(value)
        else:
            # we depend on another dependent var
            print("\n############2 dependencies level !\n", splitted[0])
            tomaplater.append(splitted[0])
    # print("varmap next:", varmap)

    # Check
    if len(tomaplater) == 0 or len(varmap) != len(vartomap):
        print("mapped", len(varmap), "values")
    else:
        raise "unmapped values"

    #debug print
    for keys,values in varmap.items():
        print(keys, values)

    # write the file with expended variables
    with open(path+".temp", "w") as tempfile:
        for line in makelines:
            newline = line
            if not '$' in newline:
                # basic line -> just write
                tempfile.write(newline+"\n")
            else:
                # needs expension
                if "wildcard" not in line:
                    # classic var e.g "$(VAR)..."
                    oldline = line
                    while newline.find("$") != -1:
                        idxstart = newline.find("$")
                        idxend = newline.find(")")
                        tempname = newline[idxstart+2:idxend]
                        try:
                            newline = newline.replace("$("+tempname+")", varmap[tempname])
                        except KeyError:
                            newline = newline.replace("$("+tempname+")", "")
                            print("ERROR : not found in varmap :", tempname)
                            if "@" in newline or "<" in newline :
                                print("ERROR : special line :", newline)
                            break
                    # write the updated line
                    tempfile.write(newline+"\n")
                else:
                    # wildcard line e.g "$(wildcard path/*.c)"
                    splitted = list(line)
                    opening = indices(line, "(")
                    closing = indices(line, ")")
                    wild = indices(line, "wildcard")
                    start = wild[0] - 1
                    opn_idx = opening.index(start)
                    cls_idx = len(closing) - 1 - opn_idx

                    # remove "$(wildcard ...)"
                    splitted[closing[cls_idx]] = "ù"
                    newline = "".join(splitted).replace("ù", "").replace("$(wildcard", "")
                    print("newline :", newline)

                    # expend the vars
                    while newline.find("$") != -1:
                        idxstart = newline.find("$")
                        idxend = newline.find(")")
                        tempname = newline[idxstart+2:idxend]
                        try:
                            newline = newline.replace("$("+tempname+")", varmap[tempname])
                        except KeyError:
                            newline = newline.replace("$("+tempname+")", "")
                            if "@" in newline or "<" in newline :
                                print("ERROR : special line :", newline)
                                break

                    # get the files
                    split = newline.split(" ")
                    for s in split:
                        if "*" in s:
                            glb = s
                    glb_path = os.path.join(directory, glb)
                    files = glob.glob(glb_path)

                    # write the full line
                    tempfile.write(split[0] + " = " + " ".join(files).replace(directory, "") + "\n")


# Makefile.temp contains only full variable names
requiredfiles = []
with open(path+".temp", "r") as maketemp:
    content = maketemp.read().split("\n")

    alltarget = []
    outputs = []
    depends = {} # map output <-> depends
    dependslist = [] # full, unmapped list
    targets = []
    patternrules = []
    for line in content:
        splitted = line.split(" ")
        if "all:" in line:
            alltarget = " ".join(splitted[1:])
        else:
            if ":" in line:
                if "%" not in line:
                    if ":" in splitted[0]:
                        # other targets : clean, test...
                        targets.append(splitted[0])
                    else:
                        # standard rules
                        outputs.append(splitted[0])
                        depends[splitted[0]] = splitted[2:]
                        for dep in splitted[2:]:
                            if dep not in dependslist and ":" not in dep:
                                dependslist.append(dep)
                else:
                    # pattern rules
                    patternrules.append(splitted[0].replace("%", ""))

    print("alltarget :\n", alltarget)
    print("outputs :\n", outputs)
    print("depends :\n", depends)
    print("targets :\n", targets)
    print("dependslist :\n", dependslist)
    print("patternrules :\n", patternrules)

    # check if a pattern rule is needed
    # == file in "depends" but not in "outputs"
    # AND there is a patternrule to generate that file
    needpatternrules = {}
    exttoignore = ["py", "sh", "genlib"]
    for dep in dependslist:
        try:
            idx = dep.index(".")
            ext = dep[idx:]
            name = dep[:idx]

            if dep not in outputs:
                if ext in patternrules:
                    # pattern rule exists to generate that file
                    if not any(ext in dep for ext in exttoignore):
                        try:
                            oldvalue = needpatternrules[ext]
                            newvalue = oldvalue + " " + name
                            needpatternrules[ext] = newvalue
                            continue
                        except KeyError:
                            needpatternrules[ext] = name
                        except ValueError:
                            pass
                else:
                    # it's a required file (ie file needs exist on disk)
                    requiredfiles.append(dep)
        except:
            print("###### . not found in", dep)


        # find empty line
    empty_lines = []
    i = 0
    for line in makelines:
        if line == "":
           empty_lines.append(i)
        i = i + 1
    print("empty_lines :", empty_lines)

    # expends the pattern rules (read in original makefile)
    print("needpatternrules :\n", needpatternrules)
    with open(path+".temp2", "w") as maketempnew:
        for line in content:
            if "%" in line:
                # pattern rule
                splitted = line.split(":")
                output = splitted[0].replace("%", "").replace(" ", "")
                input = splitted[1].split(" ")[1].replace("%", "")
                try:
                    toexpend = needpatternrules[output].split(" ")
                    startidx = content.index(line)
                    print(line, startidx, output, input)
                    print(toexpend)

                    # get the rest of the pattern rule
                    nextemptyline = findFirstGreaterThanValueInList(startidx, empty_lines)
                    print("block end at line", startidx, nextemptyline)
                    rest_of_rule = content[startidx+1:nextemptyline]
                    print("rest_of_rule :", rest_of_rule)

                    # expend the rule
                    for exp in toexpend:
                        print("exp :", exp)
                        templine = line.replace("%", exp)
                        maketempnew.write(templine + "\n")

                        # write the rest
                        for rest in rest_of_rule:
                            templine = rest.replace("$*", exp)
                            templine = templine.replace("$("+tempname+")", varmap[tempname])
                            maketempnew.write(templine + "\n")
                except KeyError:
                    print(output, "pattern rule not needed")
                    pass
            else:
                # standard line : just output
                # filter-out pattern rule
                if "$" not in line:
                    maketempnew.write(line+"\n")

# check the required files
print("requiredfiles :\n", requiredfiles)
for fil in requiredfiles:
    fullpath = os.path.join(directory, fil)
    if not os.path.exists(fullpath):
        print("### ERROR :", fullpath, "is required")


# NINJA / CMAKE ?
