import sys
import os

# Default path
optionsFilePath = os.path.join(os.path.dirname(__file__), "options.ini")

# Check for custom .ini in command line arguments
for arg in sys.argv[1:]:
    if arg.endswith(".ini"):
        if os.path.exists(arg):
            optionsFilePath = os.path.abspath(arg)
            # We don't print here yet because the logger isn't always ready
            break
        else:
            print(f"Warning: Configuration file '{arg}' not found. Using default.")

def importData(filePath=optionsFilePath):
    retList = {}
    with open(filePath,"r") as optionsFile:
        optionsData = optionsFile.read().splitlines()
    for line in optionsData:
        if "=" in line:
            option, value = line.split("=", 1)
            retList[option.strip()] = value.strip()
    
    return retList

def editData(option,value,filePath=optionsFilePath): #unused
    newOptionsData = ""
    with open(filePath,"r") as optionsFile:
        optionsData = optionsFile.read()
    for line in optionsData.splitlines():
        key = line.split("=")[0]
        if key == option:
            newOptionsData += option+"="+value+"\n"
        else:
            newOptionsData += line + "\n"

    newOptionsData = newOptionsData[:-1]
    with open(filePath,"w") as optionsFile:
        optionsFile.write(newOptionsData)
      
