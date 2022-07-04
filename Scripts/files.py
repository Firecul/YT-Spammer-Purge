#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
from copy import copy
import platform
import tarfile
from Scripts.shared_imports import *
from Scripts.utils import choice

from datetime import datetime, date, timedelta
from configparser import ConfigParser
from pkg_resources import parse_version
from random import randrange
from shutil import copyfile, move, rmtree
from itertools import islice

import io
import json
import requests
import zipfile
import time
import hashlib
import pathlib
import pickle

########################### Check Lists Updates ###########################
def check_lists_update(spamListDict, silentCheck=False):
    SpamListFolder = spamListDict["Meta"]["SpamListFolder"]
    currentListVersion = spamListDict["Meta"]["VersionInfo"]["LatestLocalVersion"]

    def update_last_checked():
        currentDate = datetime.today().strftime("%Y.%m.%d.%H.%M")
        # Update Dictionary with latest release gotten from API
        spamListDict["Meta"]["VersionInfo"].update(
            {"LatestLocalVersion": latestRelease}
        )
        spamListDict["Meta"]["VersionInfo"].update({"LastChecked": currentDate})

        # Prepare data for json file update, so only have to check once a day automatically
        newJsonContents = json.dumps(
            {"LatestRelease": latestRelease, "LastChecked": currentDate}
        )
        with open(
            spamListDict["Meta"]["VersionInfo"]["Path"], "w", encoding="utf-8"
        ) as file:
            json.dump(newJsonContents, file, indent=4)

    if silentCheck == False:
        print("\nChecking for updates to spam lists...")  # fmt: skip

    if os.path.isdir(SpamListFolder):
        pass
    else:
        try:
            os.mkdir(SpamListFolder)
        except:
            print("Error: Could not create folder. Try creating a folder called 'spam_lists' to update the spam lists.")  # fmt: skip

    try:
        response = requests.get(
            "https://api.github.com/repos/ThioJoe/YT-Spam-Domains-List/releases/latest"
        )
        if response.status_code != 200:
            if response.status_code == 403:
                if silentCheck == False:
                    print(f"\n{B.RED}{F.WHITE}Error [U-4L]:{S.R} Got an 403 (ratelimit_reached) when attempting to check for spam list update.")  # fmt: skip
                    print(f"This means you have been {F.YELLOW}rate limited by github.com{S.R}. Please try again in a while.\n")  # fmt: skip
                    return False
                else:
                    return spamListDict
            else:
                if silentCheck == False:
                    print(f"{B.RED}{F.WHITE}Error [U-3L]:{S.R} Got non 200 status code (got: {response.status_code}) when attempting to check for spam list update.\n")  # fmt: skip
                    print(f"If this keeps happening, you may want to report the issue here: https://github.com/ThioJoe/YT-Spammer-Purge/issues")  # fmt: skip
                    if silentCheck == False:
                        return False
                else:
                    return spamListDict
        latestRelease = response.json()["tag_name"]
    except OSError as ox:
        if silentCheck == True:
            return spamListDict
        else:
            if "WinError 10013" in str(ox):
                print(f"{B.RED}{F.WHITE}WinError 10013:{S.R} The OS blocked the connection to GitHub. Check your firewall settings.\n")  # fmt: skip
                return False
    except:
        if silentCheck == True:
            return spamListDict
        else:
            print("Error: Could not get latest release info from GitHub. Please try again later.")  # fmt: skip
            return False

    # If update available
    if currentListVersion == None or (
        parse_version(latestRelease) > parse_version(currentListVersion)
    ):
        print("\n>  A new spam list update is available. Downloading...")  # fmt: skip
        fileName = response.json()["assets"][0]["name"]
        total_size_in_bytes = response.json()["assets"][0]["size"]
        downloadFilePath = SpamListFolder + fileName
        downloadURL = response.json()["assets"][0]["browser_download_url"]
        filedownload = getRemoteFile(
            downloadURL, stream=True
        )  # These headers required to get correct file size
        block_size = 1048576  # 1 MiB in bytes

        with open(downloadFilePath, "wb") as file:
            for data in filedownload.iter_content(block_size):
                file.write(data)

        if os.stat(downloadFilePath).st_size == total_size_in_bytes:
            # Unzip files into folder and delete zip file
            attempts = 0
            print("Extracting updated lists...")  # fmt: skip
            # While loop continues until file no longer exists, or too many errors
            while True:
                try:
                    attempts += 1
                    time.sleep(0.5)
                    with zipfile.ZipFile(downloadFilePath, "r") as zip_ref:
                        zip_ref.extractall(SpamListFolder)
                    os.remove(downloadFilePath)
                except PermissionError as e:
                    if attempts <= 10:
                        continue
                    else:
                        traceback.print_exc()
                        print(f"\n> {F.RED}Error:{S.R} The zip file containing the spam lists was downloaded, but there was a problem extracting the files because of a permission error. ")  # fmt: skip
                        print(f"This can happen if an antivirus takes a while to scan the file. You may need to manually extract the zip file.")  # fmt: skip
                        input("\nPress enter to Continue anyway...")  # fmt: skip
                        break
                # THIS MEANS SUCCESS, the zip file was deleted after extracting, so returns
                except FileNotFoundError:
                    update_last_checked()
                    return spamListDict

        elif (
            total_size_in_bytes != 0
            and os.stat(downloadFilePath).st_size != total_size_in_bytes
        ):
            os.remove(downloadFilePath)
            print(f" > {F.RED} File did not fully download. Please try again later.\n")  # fmt: skip
            return spamListDict
    else:
        update_last_checked()
        return spamListDict


############################# Check For App Update ##############################
def check_for_update(currentVersion, updateReleaseChannel, silentCheck=False):
    isUpdateAvailable = False
    print("\nGetting info about latest updates...")  # fmt: skip

    try:
        if updateReleaseChannel == "stable":
            response = requests.get(
                "https://api.github.com/repos/ThioJoe/YT-Spammer-Purge/releases/latest"
            )
        elif updateReleaseChannel == "all":
            response = requests.get(
                "https://api.github.com/repos/ThioJoe/YT-Spammer-Purge/releases"
            )

        if response.status_code != 200:
            if response.status_code == 403:
                if silentCheck == False:
                    print(f"\n{B.RED}{F.WHITE}Error [U-4]:{S.R} Got an 403 (ratelimit_reached) when attempting to check for update.")  # fmt: skip
                    print(f"This means you have been {F.YELLOW}rate limited by github.com{S.R}. Please try again in a while.\n")  # fmt: skip
                else:
                    print(f"\n{B.RED}{F.WHITE}Error [U-4]:{S.R} Got an 403 (ratelimit_reached) when attempting to check for update.")  # fmt: skip
                return None

            else:
                if silentCheck == False:
                    print(f"{B.RED}{F.WHITE}Error [U-3]:{S.R} Got non 200 status code (got: {response.status_code}) when attempting to check for update.\n")  # fmt: skip
                    print(f"If this keeps happening, you may want to report the issue here: https://github.com/ThioJoe/YT-Spammer-Purge/issues")  # fmt: skip
                else:
                    print(f"{B.RED}{F.WHITE}Error [U-3]:{S.R} Got non 200 status code (got: {response.status_code}) when attempting to check for update.\n")  # fmt: skip
                return None

        else:
            # assume 200 response (good)
            if updateReleaseChannel == "stable":
                latestVersion = response.json()["name"]
                isBeta = False
            elif updateReleaseChannel == "all":
                latestVersion = response.json()[0]["name"]
                isBeta = response.json()[0]["prerelease"]
    except OSError as ox:
        if "WinError 10013" in str(ox):
            print(f"{B.RED}{F.WHITE}WinError 10013:{S.R} The OS blocked the connection to GitHub. Check your firewall settings.\n")  # fmt: skip
        else:
            print(f"{B.RED}{F.WHITE}Unknown OSError{S.R} Error occurred while checking for updates\n")  # fmt: skip
        return None
    except Exception as e:
        if silentCheck == False:
            print(e + "\n")  # fmt: skip
            print(f"{B.RED}{F.WHITE}Error [Code U-1]:{S.R} Problem while checking for updates. See above error for more details.\n")  # fmt: skip
            print("If this keeps happening, you may want to report the issue here: https://github.com/ThioJoe/YT-Spammer-Purge/issues")  # fmt: skip
        elif silentCheck == True:
            print(f"{B.RED}{F.WHITE}Error [Code U-1]:{S.R} Unknown problem while checking for updates. See above error for more details.\n")  # fmt: skip
        return None

    if parse_version(latestVersion) > parse_version(currentVersion):
        if isBeta == True:
            isUpdateAvailable = "beta"
        else:
            isUpdateAvailable = True

        if silentCheck == False:
            print("------------------------------------------------------------------------------------------")  # fmt: skip
            if isBeta == True:
                print(f" {F.YELLOW}A new {F.LIGHTGREEN_EX}beta{F.YELLOW} version{S.R} is available! Visit {F.YELLOW}TJoe.io/latest{S.R} to see what's new.")  # fmt: skip
            else:
                print(f" A {F.LIGHTGREEN_EX}new version{S.R} is available! Visit {F.YELLOW}TJoe.io/latest{S.R} to see what's new.")  # fmt: skip
            print(f"   > Current Version: {currentVersion}")  # fmt: skip
            print(f"   > Latest Version: {F.LIGHTGREEN_EX}{latestVersion}{S.R}")  # fmt: skip
            if isBeta == True:
                print("(To stop receiving beta releases, change the 'release_channel' setting in the config file)")  # fmt: skip
            print("------------------------------------------------------------------------------------------")  # fmt: skip
            userChoice = choice("Update Now?")
            if userChoice == True:
                if sys.platform == "win32" or sys.platform == "win64":
                    print(f"\n> {F.LIGHTCYAN_EX} Downloading Latest Version...{S.R}")  # fmt: skip
                    if updateReleaseChannel == "stable":
                        jsondata = json.dumps(response.json()["assets"])
                    elif updateReleaseChannel == "all":
                        jsondata = json.dumps(response.json()[0]["assets"])
                    dict_json = json.loads(jsondata)

                    # Get files in release, get exe and hash info
                    i, j, k = (
                        0,
                        0,
                        0,
                    )  # i = index of all, j = index of exe, k = index of hash
                    for asset in dict_json:
                        i += 1
                        name = str(asset["name"])
                        if ".exe" in name.lower():
                            filedownload = requests.get(
                                dict_json[0]["browser_download_url"], stream=True
                            )
                            j += 1  # Count number of exe files in release, in case future has multiple exe's, can cause warning
                        if ".sha256" in name.lower():
                            # First removes .sha256 file extension, then removes all non-alphanumeric characters
                            downloadHashSHA256 = re.sub(
                                r"[^a-zA-Z0-9]", "", name.lower().replace(".sha256", "")
                            )
                            k += 1

                    ignoreHash = False
                    # Validate Retrieved Info
                    if j > 1:  # More than one exe file in release
                        print(f"{F.YELLOW}Warning!{S.R} Multiple exe files found in release. You must be updating from the future when that was not anticipated.")  # fmt: skip
                        print("You should instead manually download the latest version from: https://github.com/ThioJoe/YT-Spammer-Purge/releases")  # fmt: skip
                        print("You can try continuing anyway, but it might not be successful, or might download the wrong exe file.")  # fmt: skip
                        input("\nPress enter to continue...")  # fmt: skip
                    elif j == 0:  # No exe file in release
                        print(f"{F.LIGHTRED_EX}Warning!{S.R} No exe file found in release. You'll have to manually download the latest version from:")  # fmt: skip
                        print("https://github.com/ThioJoe/YT-Spammer-Purge/releases")  # fmt: skip
                        return False
                    if k == 0:  # No hash file in release
                        print(f"{F.YELLOW}Warning!{S.R} No verification sha256 hash found in release. If download fails, you can manually download latest version here:")  # fmt: skip
                        print("https://github.com/ThioJoe/YT-Spammer-Purge/releases")  # fmt: skip
                        input("\nPress Enter to try to continue...")  # fmt: skip
                        ignoreHash = True
                    elif k > 0 and k != j:
                        print(f"{F.YELLOW}Warning!{S.R} Too many or too few sha256 files found in release. If download fails, you should manually download latest version here:")  # fmt: skip
                        print("https://github.com/ThioJoe/YT-Spammer-Purge/releases")  # fmt: skip
                        input("\nPress Enter to try to continue...")  # fmt: skip

                    # Get and Set Download Info
                    total_size_in_bytes = int(
                        filedownload.headers.get("content-length", 0)
                    )
                    block_size = 1048576  # 1 MiB in bytes
                    downloadFileName = dict_json[0]["name"]

                    # Check if file exists already, ask to overwrite if it does
                    if os.path.exists(downloadFileName):
                        print(f"\n{B.RED}{F.WHITE} WARNING! {S.R} '{F.YELLOW}{downloadFileName}{S.R}' file already exists. This would overwrite the existing file.")  # fmt: skip
                        confirm = choice("Overwrite this existing file?")
                        if confirm == True:
                            try:
                                os.remove(downloadFileName)
                            except:
                                traceback.print_exc()
                                print(f"\n{F.LIGHTRED_EX}Error F-6:{S.R} Problem deleting existing existing file! Check if it's gone, or delete it yourself, then try again.")  # fmt: skip
                                print("The info above may help if it's a bug, which you can report here: https://github.com/ThioJoe/YT-Spammer-Purge/issues")  # fmt: skip
                                input("Press enter to Exit...")  # fmt: skip
                                sys.exit()
                        elif confirm == False or confirm == None:
                            return False

                    # Download File
                    with open(downloadFileName, "wb") as file:
                        numProgressBars = 30
                        for data in filedownload.iter_content(block_size):
                            progress = (
                                os.stat(downloadFileName).st_size
                                / total_size_in_bytes
                                * numProgressBars
                            )
                            print(
                                f"{F.LIGHTGREEN_EX}<[{F.LIGHTCYAN_EX}"
                                + "=" * round(progress)
                                + " " * (numProgressBars - round(progress))
                                + f"{F.LIGHTGREEN_EX}]>{S.R}\r",
                                end="",
                            )  # fmt: skip#Print Progress bar
                            file.write(data)
                    print(f"\n>  {F.LIGHTCYAN_EX}Verifying Download Integrity...{S.R}                       ")  # fmt: skip

                    # Verify Download Size
                    if os.stat(downloadFileName).st_size == total_size_in_bytes:
                        pass
                    elif (
                        total_size_in_bytes != 0
                        and os.stat(downloadFileName).st_size != total_size_in_bytes
                    ):
                        os.remove(downloadFileName)
                        print(f"\n> {F.RED} File did not fully download. Please try again later.")  # fmt: skip
                        return False
                    elif total_size_in_bytes == 0:
                        print("Something is wrong with the download on the remote end. You should manually download latest version here:")  # fmt: skip
                        print("https://github.com/ThioJoe/YT-Spammer-Purge/releases")  # fmt: skip

                    # Verify hash
                    if ignoreHash == False:
                        if (
                            downloadHashSHA256
                            == hashlib.sha256(open(downloadFileName, "rb").read())
                            .hexdigest()
                            .lower()
                        ):
                            pass
                        else:
                            os.remove(downloadFileName)
                            print(f"\n> {F.RED} Hash did not match. Please try again later.")  # fmt: skip
                            print("Or download the latest version manually from here: https://github.com/ThioJoe/YT-Spammer-Purge/releases")  # fmt: skip
                            return False
                    print(f"\n >  Download Completed: {F.LIGHTGREEN_EX}{downloadFileName}{S.R}")  # fmt: skip
                    if isBeta == False:
                        print("\nYou can now delete the old version. (Or keep it around in case you encounter any issues with the new version)")  # fmt: skip
                    else:
                        print(f"\n{F.LIGHTYELLOW_EX}NOTE:{S.R} Because this is a {F.CYAN}beta release{S.R}, you should keep the old version around in case you encounter any issues")  # fmt: skip
                        print(f" > And don't forget to report any problems you encounter here: {F.YELLOW}TJoe.io/bug-report{S.R}")  # fmt: skip
                    input("\nPress Enter to Exit...")  # fmt: skip
                    sys.exit()
                elif platform.system() == "Linux":
                    # Current working directory
                    cwd = os.getcwd()
                    # what we want the tar file to be called on the system
                    tarFileName = "yt-spammer.tar.gz"
                    # Name of this file
                    # Temp folder for update
                    stagingFolder = "temp"
                    print(f"\n> Downloading version: {F.GREEN}{latestVersion}{S.R}")  # fmt: skip

                    url = f"https://codeload.github.com/ThioJoe/YT-Spammer-Purge/tar.gz/refs/tags/v{latestVersion}"
                    r = requests.get(url, stream=True)
                    if r.status_code == 200:
                        with open(tarFileName, "wb") as file:
                            for chunk in r.iter_content(chunk_size=1048576):
                                if chunk:
                                    file.write(chunk)
                    else:
                        print("Downloading of new version failed!")  # fmt: skip
                        print(f"\n> {F.RED}Error: {S.R}GitHub returned a non 200 status code while trying to download newer version.\nStatus returned: {r.status_code}")  # fmt: skip
                        input("Press Enter to Exit...")  # fmt: skip
                        sys.exit()
                    print("\n> Extracting...")  # fmt: skip
                    with tarfile.open(tarFileName) as file:
                        file.extractall(f"./{stagingFolder}")
                    os.remove(tarFileName)
                    print(f"> Installing...")  # fmt: skip
                    # Retrieve the name of the folder containing the main file, we are assuming there will always be only one folder here
                    extraFolderPath = os.listdir(f"./{stagingFolder}")
                    # If there happens to be more then one folder
                    if len(extraFolderPath) != 1:
                        print(f"\n> {F.RED} Error:{S.R} more then one folder in {stagingFolder}! Please make a bug report.")  # fmt: skip
                        print(f"\n{F.RED}Aborting Update!{S.R}")  # fmt: skip
                        print("\n> Cleaning up...")  # fmt: skip
                        rmtree(stagingFolder)
                        input("\nPress Enter to Exit...")  # fmt: skip
                        sys.exit()
                    else:
                        extraFolderPath = f"{cwd}/{stagingFolder}/{extraFolderPath[0]}"

                        for file_name in os.listdir(extraFolderPath):
                            if os.path.exists(file_name):
                                try:
                                    os.remove(file_name)
                                except IsADirectoryError:
                                    rmtree(file_name)
                                move(
                                    f"{extraFolderPath}/{file_name}",
                                    f"{cwd}/{file_name}",
                                )

                    rmtree(stagingFolder)
                    print(f"\n> Update completed: {currentVersion} ==> {F.GREEN}{latestVersion}{S.R}")  # fmt: skip
                    print("> Restart the script to apply the update.")  # fmt: skip
                    input("\nPress Enter to Exit...")  # fmt: skip
                    sys.exit()

                else:
                    print(f"> {F.RED} Error:{S.R} You are using an unsupported OS for the autoupdater (macos). \n This updater only supports Windows and Linux (right now). Feel free to get the files from github: https://github.com/ThioJoe/YT-Spammer-Purge")  # fmt: skip
                    return False
            elif userChoice == "False" or userChoice == None:
                return False
        elif silentCheck == True:
            return isUpdateAvailable

    elif parse_version(latestVersion) == parse_version(currentVersion):
        if silentCheck == False:
            print(f"\nYou have the {F.LIGHTGREEN_EX}latest{S.R} version: {F.LIGHTGREEN_EX}" + currentVersion)  # fmt: skip
        return False
    else:
        if silentCheck == False:
            print("\nNo newer release available - Your Version: " + currentVersion + "  --  Latest Version: " + latestVersion)  # fmt: skip
        return False


######################### Try To Get Remote File ##########################
def getRemoteFile(url, stream, silent=False, headers=None):
    try:
        if stream == False:
            response = requests.get(url, headers=headers)
        elif stream == True:
            response = requests.get(url, headers=headers, stream=True)
        if response.status_code != 200:
            if silent == False:
                print("Error fetching remote file or resource: " + url)  # fmt: skip
                print("Response Code: " + str(response.status_code))  # fmt: skip
        else:
            return response

    except Exception as e:
        if silent == False:
            print(e + "\n")  # fmt: skip
            print(f"{B.RED}{F.WHITE} Error {S.R} While Fetching Remote File or Resource: " + url)  # fmt: skip
            print("See above messages for details.\n")  # fmt: skip
            print("If this keeps happening, you may want to report the issue here: https://github.com/ThioJoe/YT-Spammer-Purge/issues")  # fmt: skip
        return None


############################# Load a Config File ##############################
# Put config settings into dictionary
def load_config_file(
    configVersion=None,
    forceDefault=False,
    skipConfigChoice=False,
    configFileName="SpamPurgeConfig.ini",
    configFolder="configs",
):
    configDict = {}

    def default_config_path(relative_path):
        if hasattr(sys, "_MEIPASS"):  # If running as a pyinstaller bundle
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(
            os.path.abspath("assets"), relative_path
        )  # If running as script, specifies resource folder as /assets

    # First find where main config file is, if any
    # First check in current directory
    if forceDefault == False and os.path.exists(configFileName):
        default = False
        currentConfigPath = os.path.dirname(configFileName)
        currentConfigFileNameWithPath = os.path.abspath(configFileName)
    # Otherwise check if config is in configFolder
    elif forceDefault == False and os.path.exists(
        os.path.join(configFolder, os.path.basename(configFileName))
    ):
        default = False
        currentConfigPath = os.path.abspath(configFolder)
        currentConfigFileNameWithPath = os.path.join(
            currentConfigPath, os.path.basename(configFileName)
        )
    else:
        currentConfigFileNameWithPath = default_config_path("default_config.ini")
        default = True

    # Load Contents of config file
    try:
        with open(currentConfigFileNameWithPath, "r", encoding="utf-8") as configFile:
            configData = configFile.read()
            configFile.close()
    except:
        traceback.print_exc()
        print(f"{B.RED}{F.WHITE}Error Code: F-4{S.R} - Config file found, but there was a problem loading it! The info above may help if it's a bug.")  # fmt: skip
        print("\nYou can manually delete SpamPurgeConfig.ini and use the program to create a new default config.")  # fmt: skip
        input("Press enter to Exit...")  # fmt: skip
        sys.exit()

    # Sanitize config Data by removing quotes
    configData = configData.replace("'", "")
    configData = configData.replace('"', "")

    # Converts string from config file, wraps it to make it behave like file so it can be read by parser
    # Must use .read_file, .read doesn't work
    wrappedConfigData = io.StringIO(configData)
    parser = ConfigParser()
    parser.read_file(wrappedConfigData)

    # Convert raw config dictionary into easier to use dictionary
    settingsToKeepCase = [
        "your_channel_id",
        "videos_to_scan",
        "channel_ids_to_filter",
        "regex_to_filter",
        "channel_to_scan",
        "log_path",
        "this_config_description",
        "configs_path",
    ]
    validWordVars = ["ask", "mine", "default"]
    for section in parser.sections():
        for setting in parser.items(section):
            # Setting[0] is name of the setting, Setting[1] is the value of the setting
            if (
                setting[0] in settingsToKeepCase
                and setting[1].lower() not in validWordVars
            ):
                configDict[setting[0]] = setting[1]
            else:
                # Take values out of raw dictionary structure and put into easy dictionary with processed values
                configDict[setting[0]] = setting[1].lower()
                if setting[1].lower() == "false":
                    configDict[setting[0]] = False
                elif setting[1].lower() == "true":
                    configDict[setting[0]] = True

    # Prevent prompt about config file if it's the default config file
    if default == True:
        configDict["use_this_config"] = True
    # ----------------------------------------------------------------------------------------------------------------------
    # Check if config out of date, update, ask to use config or not
    else:
        if configDict["use_this_config"] == False:
            configDict = load_config_file(forceDefault=True)
        elif (
            configDict["use_this_config"] == "ask"
            or configDict["use_this_config"] == True
        ):
            if configVersion != None:
                configDict = check_update_config_file(
                    configVersion, configDict, currentConfigFileNameWithPath
                )
            if configDict["use_this_config"] == True or skipConfigChoice == True:
                pass
            else:
                configDict = choose_config_file(
                    configDict, configVersion, currentConfigFileNameWithPath
                )

        else:
            print("Error C-1: Invalid value in config file for setting 'use_this_config' - Must be 'True', 'False', or 'Ask'")  # fmt: skip
            input("Press Enter to exit...")  # fmt: skip
            sys.exit()

    return configDict


############################# Check for Config Update ##############################
def check_update_config_file(newVersion, existingConfig, configFileNameWithPath):
    backupDestinationFolder = os.path.join(RESOURCES_FOLDER_NAME, "User_Config_Backups")
    try:
        existingConfigVersion = int(existingConfig["config_version"])
        if existingConfigVersion < newVersion:
            configOutOfDate = True
        else:
            configOutOfDate = False
    except:
        configOutOfDate = True

    if configOutOfDate == True:
        print(f"\n{F.YELLOW} WARNING! {S.R} Your config file is {F.YELLOW}out of date{S.R}. ")  # fmt: skip
        print(f"  > Program will {F.LIGHTGREEN_EX}update your config{S.R} now, {F.LIGHTGREEN_EX}back up the old file{S.R}, and {F.LIGHTGREEN_EX}copy your settings over{S.R})")  # fmt: skip
        input("\nPress Enter to update config file...")  # fmt: skip
    else:
        return existingConfig

    # If user config file exists, keep path. Otherwise use default config file path
    if os.path.exists(configFileNameWithPath):
        pass
    else:
        print("No existing config file found!")  # fmt: skip
        return False

    # Load data of old config file
    with open(configFileNameWithPath, "r", encoding="utf-8") as oldFile:
        oldConfigData = oldFile.readlines()
        oldFile.close()

    # Rename config to backup and copy to backup folder
    if not os.path.exists(backupDestinationFolder):
        os.mkdir(backupDestinationFolder)
    backupConfigFileName = (
        f"{os.path.basename(configFileNameWithPath)}.backup_v{existingConfigVersion}"
    )
    backupNameAndPath = os.path.join(backupDestinationFolder, backupConfigFileName)
    if os.path.isfile(backupNameAndPath):
        print("Existing backup config file found. Random number will be added to new backup file name.")  # fmt: skip
        while os.path.isfile(backupNameAndPath):
            backupConfigFileName = backupConfigFileName + "_" + str(randrange(999))
            backupNameAndPath = os.path.join(
                backupDestinationFolder, backupConfigFileName
            )

    # Attempt to copy backup to backup folder, otherwise just rename
    try:
        copyfile(configFileNameWithPath, os.path.abspath(backupNameAndPath))
        print(f"\nOld config file renamed to {F.CYAN}{backupConfigFileName}{S.R} and placed in {F.CYAN}{backupDestinationFolder}{S.R}")  # fmt: skip
    except:
        os.rename(configFileNameWithPath, backupConfigFileName)
        print(f"\nOld config file renamed to {F.CYAN}{backupConfigFileName}{S.R}. Note: Backup file could not be moved to backup folder, so it was just renamed.")  # fmt: skip

    # Creates new config file from default
    create_config_file(updating=True, configFileName=configFileNameWithPath)

    try:
        with open(configFileNameWithPath, "r", encoding="utf-8") as newFile:
            newConfigData = newFile.readlines()

        newDataList = []
        # Go through all new config lines
        for newLine in newConfigData:
            if (
                not newLine.strip().startswith("#")
                and not newLine.strip().startswith("[")
                and not newLine.strip() == ""
                and "version" not in newLine
            ):
                for setting in existingConfig.keys():
                    # Check if any old settings are in new config file
                    newLineStripped = newLine.strip().replace(" ", "")
                    if (
                        newLineStripped.startswith(setting)
                        and newLineStripped[0 : newLineStripped.rindex("=")] == setting
                    ):  # Avoids having to use startswith(), which messes up if setting names start the same
                        for oldLine in oldConfigData:
                            oldLineStripped = oldLine.strip().replace(" ", "")
                            if (
                                not oldLine.strip().startswith("#")
                                and not newLine.strip().startswith("[")
                                and not oldLine.strip() == ""
                                and "version" not in oldLine
                            ):
                                # Sets new line to be the old line
                                if (
                                    oldLineStripped.startswith(setting)
                                    and oldLineStripped[0 : oldLineStripped.rindex("=")]
                                    == setting
                                ):
                                    newLine = oldLine
                                    break
                        break
            # The new config file writes itself again, but with the modified newLine's
            newDataList.append(newLine)
        success = False
        attempts = 0
        while success == False:
            try:
                attempts += 1
                with open(configFileNameWithPath, "w", encoding="utf-8") as newFile:
                    newFile.writelines(newDataList)
                success = True
            except PermissionError:
                if attempts < 3:
                    print(f"\n{F.YELLOW}\nERROR!{S.R} Cannot write to {F.LIGHTCYAN_EX}{os.path.relpath(configFileNameWithPath)}{S.R}. Is it open? Try {F.YELLOW}closing the file{S.R} before continuing.")  # fmt: skip
                    input("\n Press Enter to Try Again...")  # fmt: skip
                else:
                    print(f"{F.LIGHTRED_EX}\nERROR! Still cannot write to {F.LIGHTCYAN_EX}{os.path.relpath(configFileNameWithPath)}{F.LIGHTRED_EX}. {F.YELLOW}Try again?{S.R} (Y) or {F.YELLOW}Skip Updating Config (May Cause Errors)?{S.R} (N)")  # fmt: skip
                    if choice("Choice:") == False:
                        break

        return load_config_file(
            configVersion=None,
            skipConfigChoice=True,
            configFileName=configFileNameWithPath,
        )
    except:
        traceback.print_exc()
        print("--------------------------------------------------------------------------------")  # fmt: skip
        print("Something went wrong when copying your config settings. You'll have to manually copy them from backup.")  # fmt: skip
        input("\nPress Enter to exit...")  # fmt: skip
        sys.exit()


############################# Get List of Files Matching Regex ##############################
def list_config_files(configDict=None, configPath=None):
    configNumExpression = r"(?<=spampurgeconfig)(\d+?)(?=\.ini)"

    if configDict:
        altConfigPath = configDict["configs_path"]
    else:
        altConfigPath = None

    # Check same folder as program
    if configPath == None:
        path = os.getcwd()
    else:
        if not os.path.isabs(configPath):
            path = os.path.abspath(configPath)
        else:
            path = configPath

    # Check path listed in config file
    if altConfigPath and os.path.isdir(altConfigPath):
        if not os.path.isabs(altConfigPath):
            altPath = os.path.abspath(altConfigPath)
        else:
            altPath = altConfigPath
    else:
        altPath = None

    # List files in current directory, only get non-primary log files
    def list_path_files(pathToSearch):
        fileList = list()
        if os.listdir(pathToSearch):
            for file in os.listdir(pathToSearch):
                if (
                    "spampurgeconfig" in file.lower()
                    and file.lower() != "spampurgeconfig.ini"
                ):
                    try:
                        match = re.search(configNumExpression, file.lower()).group(0)
                        # Only exact matches, no backups
                        if file.lower() == "spampurgeconfig" + match + ".ini":
                            fileList.append(file)
                    except AttributeError as ax:
                        if "NoneType" in str(ax):
                            pass
                        else:
                            traceback.print_exc()
                            print("--------------------------------------------------------------------------------")  # fmt: skip
                            print("Something went wrong when getting list of config files. Check your regex.")  # fmt: skip
                            input("\nPress Enter to exit...")  # fmt: skip
                            sys.exit()

        return fileList

    # First get list of configs from the directory in main config file
    if altPath != None:
        altDirFiles = list_path_files(altPath)
        if altDirFiles:
            return altDirFiles, altPath

    # If no configs found in specified config path, check current directory
    if path != None:
        currentDirFiles = list_path_files(path)
        if currentDirFiles:
            return currentDirFiles, path

    # Otherwise return nothing
    return None, None


############################# Ask to use Config or Which One ##############################
# Applies if not using default config, and if not set to 'not use' config
def choose_config_file(configDict, newestConfigVersion, configPathWithName):
    configNumExpression = r"(?<=spampurgeconfig)(\d+?)(?=\.ini)"
    configPath = os.path.dirname(configPathWithName)
    configFileList, configPath = list_config_files(configDict, configPath)
    # If only one config file exists, prompt to use
    if not configFileList or len(configFileList) == 0:
        if choice(f"\nFound {F.YELLOW}config file{S.R}, use those settings?") == False:
            return load_config_file(forceDefault=True)
        else:
            return configDict

    if os.path.exists(os.path.join(configPath, "SpamPurgeConfig.ini")):
        mainConfigPathWithName = os.path.join(configPath, "SpamPurgeConfig.ini")
    elif os.path.exists("SpamPurgeConfig.ini"):
        mainConfigPathWithName = "SpamPurgeConfig.ini"
    else:
        mainConfigPathWithName = None

    # If more than one config exists, list and ask which
    if configFileList and len(configFileList) > 0:
        configChoiceDict = {}
        print(f"\n=================== Found Multiple Config Files ===================")  # fmt: skip
        if mainConfigPathWithName:
            print(f"\n{F.YELLOW}------------- Use primary config file or another one? -------------{S.R}")  # fmt: skip
            print(F"    {F.LIGHTCYAN_EX}Y:{S.R} Use primary config file")  # fmt: skip
            print(F"    {F.LIGHTCYAN_EX}N:{S.R} Use default settings, don't load any config")  # fmt: skip
            print(f"\n{F.YELLOW}------------------ Other Available Config Files -------------------{S.R}")  # fmt: skip
        else:
            print("\n Available Config Files:")  # fmt: skip
        # Print Available Configs, and add to dictionary
        for file in configFileList:
            configNum = re.search(configNumExpression, file.lower()).group(0)
            configDescription = load_config_file(
                configFileName=os.path.abspath(os.path.join(configPath, file)),
                skipConfigChoice=True,
                configFolder=configPath,
            )["this_config_description"]
            configChoiceDict[configNum] = file
            print(f"    {F.LIGHTCYAN_EX}{configNum}:{S.R} {configDescription}")  # fmt: skip

        valid = False
        while valid == False:
            configChoice = input("\n Config Choice (Y/N or #): ")  # fmt: skip
            if configChoice.lower() == "y":
                return configDict
            elif configChoice.lower() == "n":
                return load_config_file(forceDefault=True)
            elif (
                configChoice.lower() == ""
                or configChoice.lower() not in configChoiceDict.keys()
            ):
                print(f"\n{F.YELLOW} Invalid Choice! Please enter a valid choice.{S.R}")  # fmt: skip
            else:
                # Load an available config, update it, then return it
                configChoiceFileNameWithPath = os.path.abspath(
                    os.path.join(configPath, configChoiceDict[configChoice])
                )
                chosenConfigDict = load_config_file(
                    skipConfigChoice=True,
                    configFileName=configChoiceFileNameWithPath,
                    configFolder=configPath,
                )
                chosenConfigDict = check_update_config_file(
                    newestConfigVersion, chosenConfigDict, configChoiceFileNameWithPath
                )
                return load_config_file(
                    skipConfigChoice=True,
                    configFileName=configChoiceFileNameWithPath,
                    configFolder=configPath,
                )


############################# Ingest Other Files ##############################
def ingest_asset_file(fileName):
    def assetFilesPath(relative_path):
        if hasattr(sys, "_MEIPASS"):  # If running as a pyinstaller bundle
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(
            os.path.abspath("assets"), relative_path
        )  # If running as script, specifies resource folder as /assets

    # Open list of root zone domain extensions
    with open(assetFilesPath(fileName), "r", encoding="utf-8") as file:
        data = file.readlines()
    dataList = []
    for line in data:
        if not line.strip().startswith("#"):
            line = line.strip()
            dataList.append(line.lower())
    return dataList


def copy_asset_file(fileName, destination):
    def assetFilesPath(relative_path):
        if hasattr(sys, "_MEIPASS"):  # If running as a pyinstaller bundle
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(
            os.path.abspath("assets"), relative_path
        )  # If running as script, specifies resource folder as /assets

    copyfile(assetFilesPath(fileName), os.path.abspath(destination))


def ingest_list_file(relativeFilePath, keepCase=True):
    if os.path.exists(relativeFilePath):
        with open(relativeFilePath, "r", encoding="utf-8") as listFile:
            # If file doesn't end with newline, add one
            listData = listFile.readlines()
            lastline = listData[-1]

        with open(relativeFilePath, "a", encoding="utf-8") as listFile:
            if not lastline.endswith("\n"):
                listFile.write("\n")

        processedList = []
        for line in listData:
            line = line.strip()
            if not line.startswith("#") and line != "":
                if keepCase == False:
                    processedList.append(line.lower())
                else:
                    processedList.append(line)
        return processedList
    else:
        return None


def get_list_file_version(relativeFilePath):
    listVersion = None
    if os.path.exists(relativeFilePath):
        matchBetweenBrackets = "(?<=\[)(.*?)(?=\])"  # Matches text between first set of two square brackets
        with open(relativeFilePath, "r", encoding="utf-8") as file:
            for line in islice(file, 0, 5):
                try:
                    matchItem = re.search(matchBetweenBrackets, line)
                    if matchItem:
                        listVersion = str(matchItem.group(0))
                        break
                except AttributeError:
                    pass
            return listVersion
    else:
        return None


############################# CONFIG FILE FUNCTIONS ##############################
def create_config_file(
    updating=False,
    dontWarn=False,
    configFileName="SpamPurgeConfig.ini",
    configDict=None,
):
    def config_path(relative_path):
        if hasattr(sys, "_MEIPASS"):  # If running as a pyinstaller bundle
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(
            os.path.abspath("assets"), relative_path
        )  # If running as script, specifies resource folder as /assets

    dirPath = ""

    if os.path.exists(configFileName) or os.path.exists(
        os.path.join(configDict["configs_path"], configFileName)
    ):
        if updating == False and dontWarn == False:
            # First get list of existing secondary config files, to know what to name the new one
            configNumExpression = r"(?<=spampurgeconfig)(\d+?)(?=\.ini)"
            configFileList, dirPath = list_config_files(configDict=configDict)
            if configFileList and len(configFileList) > 0:
                configNumList = list()
                for file in configFileList:
                    configNum = re.search(configNumExpression, file.lower()).group(0)
                    configNumList.append(int(configNum))
                newConfigNum = max(configNumList) + 1
            else:
                newConfigNum = 2
                dirPath = configDict["configs_path"]
            print("-------------------------------------------------------------------------------------")  # fmt: skip
            print(f"\nConfig File {F.YELLOW}{configFileName}{S.R} already exists. You can {F.LIGHTCYAN_EX}reset it to default{S.R}, or {F.LIGHTCYAN_EX}create another secondary config{S.R}.")  # fmt: skip
            print("\nWhat do you want to do?")  # fmt: skip
            print(f"    1: {F.LIGHTRED_EX}Reset{S.R} main config ({F.LIGHTRED_EX}{configFileName}{S.R}) to fresh default config")  # fmt: skip
            print(f"    2: {F.YELLOW}Create{S.R} another secondary config file (SpamPurgeConfig{F.YELLOW}{newConfigNum}{S.R}.ini)")  # fmt: skip
            userChoice = input("\n Choose (1/2): ")  # fmt: skip

            if userChoice.lower() == "x":
                return "MainMenu"

            elif userChoice == "1":
                # Removes existing file to make room for fresh default config
                try:
                    os.remove(configFileName)
                except:
                    traceback.print_exc()
                    print("Error Code F-1: Problem deleting existing existing file! Check if it's gone. The info above may help if it's a bug.")  # fmt: skip
                    print("If this keeps happening, you may want to report the issue here: https://github.com/ThioJoe/YT-Spammer-Purge/issues")  # fmt: skip
                    input("Press enter to Exit...")  # fmt: skip
                    sys.exit()

            elif userChoice == "2":
                configFileName = f"SpamPurgeConfig{newConfigNum}.ini"
                input(f"\nPress Enter to create additional config file: {F.YELLOW}{configFileName}{S.R}")  # fmt: skip

    # Creates fresh new config file
    # Get default config file contents
    try:
        with open(
            config_path("default_config.ini"), "r", encoding="utf-8"
        ) as defaultConfigFile:
            data = defaultConfigFile.read()
        defaultConfigFile.close()
    except:
        traceback.print_exc()
        print(f"{B.RED}{F.WHITE}Error Code: F-2{S.R} - Problem reading default config file! The info above may help if it's a bug.")  # fmt: skip
        input("Press enter to Exit...")  # fmt: skip
        sys.exit()

    # Create config file
    if dirPath != None and dirPath != "":
        configFilePathWithName = os.path.join(dirPath, configFileName)
    else:
        configFilePathWithName = configFileName

    attempts = 0
    success = False
    while success == False:
        if dirPath and not os.path.isdir(dirPath):
            try:
                os.makedirs(dirPath)
            except:
                traceback.print_exc()
                print(f"{B.RED}{F.WHITE}Error Code: F-3{S.R} - Problem creating 'configs' folder! Try creating the folder yourself.")  # fmt: skip
                input("Then Press Enter to Continue...")  # fmt: skip
        try:
            attempts += 1
            with open(configFilePathWithName, "w", encoding="utf-8") as configFile:
                configFile.write(data)
                configFile.close()
            success = True
        except PermissionError:
            if attempts < 3:
                print(f"\n{F.YELLOW}\nERROR!{S.R} Cannot write to {F.LIGHTCYAN_EX}{configFileName}{S.R}. Is it open? Try {F.YELLOW}closing the file{S.R} before continuing.")  # fmt: skip
                input("\n Press Enter to Try Again...")  # fmt: skip
            else:
                print(f"{F.LIGHTRED_EX}\nERROR! Still cannot write to {F.LIGHTCYAN_EX}{configFileName}{F.LIGHTRED_EX}. {F.YELLOW}Try again?{S.R} (Y) or {F.YELLOW}Abandon Writing Config?{S.R} (N)")  # fmt: skip
                if choice("Choice:") == False:
                    break
        except:
            traceback.print_exc()
            print(f"{B.RED}{F.WHITE}Error Code: F-3{S.R} Problem creating config file! The info above may help if it's a bug.")  # fmt: skip
            input("Press enter to Exit...")  # fmt: skip
            sys.exit()

    if os.path.exists(configFilePathWithName):
        parser = ConfigParser()
        try:
            parser.read("SpamPurgeConfig.ini", encoding="utf-8")
            if parser.get("info", "config_version"):
                if updating == False:
                    if dirPath:
                        dirString = f"{F.YELLOW}{str(dirPath)}{S.R}"
                    else:
                        dirString = "current"
                    print(f"\n{B.GREEN}{F.BLACK} SUCCESS! {S.R}  {F.YELLOW}{configFileName}{S.R} file created successfully in {dirString} folder.")  # fmt: skip
                    print(f"\nYou can now edit the file to your liking. You can also {F.YELLOW}create additional{S.R} configs using this same menu.\n")  # fmt: skip
                    input("Press Enter to return to main menu...")  # fmt: skip
                    return "MainMenu"
                else:
                    return True
            else:
                print("Something might have gone wrong. Check if SpamPurgeConfig.ini file exists and has contents.")  # fmt: skip
                input("Press enter to Exit...")  # fmt: skip
                sys.exit()
        except:
            traceback.print_exc()
            print("Something went wrong when checking the created file. Check if SpamPurgeConfig.ini exists and has text. The info above may help if it's a bug.")  # fmt: skip
            input("Press enter to Exit...")  # fmt: skip
            sys.exit()


# -------------------------------------------------------------------


def parse_comment_list(config, recovery=False, removal=False, returnFileName=False):
    if recovery == True:
        actionVerb = "recover"
        actionNoun = "recovery"
    elif removal == True:
        actionVerb = "remove"
        actionNoun = "removal"

    validFile = False
    manuallyEnter = False
    while validFile == False and manuallyEnter == False:
        print("--------------------------------------------------------------------------------")  # fmt: skip
        print(f"\nEnter the {F.YELLOW}name of the log file{S.R} with the comments to {actionVerb} (you can rename it to something easier like \'log.rtf\')")  # fmt: skip
        print(f"     > {F.BLACK}{B.LIGHTGREEN_EX} TIP: {S.R} You can just drag the file into this window instead of typing it")  # fmt: skip
        print(F"{F.YELLOW}Or:{S.R} Just hit Enter to manually paste in the list of IDs next)")  # fmt: skip
        listFileName = input("\nLog File Name (Example: \"log.rtf\" or \"log\"):  ")  # fmt: skip
        if str(listFileName).lower() == "x":
            return "MainMenu", None

        listFileName = listFileName.strip('"').strip(
            "'"
        )  # Remove quotes, if added by dragging and dropping or pasting path
        if len(listFileName) > 0:
            if os.path.exists(listFileName):
                pass
            elif os.path.exists(listFileName + ".rtf"):
                listFileName = listFileName + ".rtf"
            elif os.path.exists(listFileName + ".txt"):
                listFileName = listFileName + ".txt"
            else:
                # Try in the log folder
                listFileName = os.path.join(config["log_path"], listFileName)
                if os.path.exists(listFileName):
                    pass
                elif os.path.exists(listFileName + ".rtf"):
                    listFileName = listFileName + ".rtf"
                elif os.path.exists(listFileName + ".txt"):
                    listFileName = listFileName + ".txt"

            # Get file path
            if os.path.exists(listFileName):
                try:
                    with open(listFileName, "r", encoding="utf-8") as listFile:
                        data = listFile.read()
                    listFile.close()
                    validFile = True
                except:
                    print(f"{F.RED}Error Code F-5:{S.R} Log File was found but there was a problem reading it.")  # fmt: skip
            else:
                print(f"\n{F.LIGHTRED_EX}Error: File not found.{S.R} Make sure it is in the same folder as the program.\n")  # fmt: skip
                print(f"Enter '{F.YELLOW}Y{S.R}' to try again, or '{F.YELLOW}N{S.R}' to manually paste in the comment IDs.")  # fmt: skip
                userChoice = choice("Try entering file name again?")
                if userChoice == True:
                    pass
                elif userChoice == False:
                    manuallyEnter = True
                elif userChoice == None:
                    return "MainMenu", None
        else:
            manuallyEnter = True

    if manuallyEnter == True:
        print("\n\n--- Manual Comment ID Entry Instructions ---")  # fmt: skip
        print(f"1. {F.YELLOW}Open the log file{S.R} and look for where it shows the list of {F.YELLOW}\"IDs of Matched Comments\".{S.R}")  # fmt: skip
        print(f"2. {F.YELLOW}Copy that list{S.R}, and {F.YELLOW}paste it below{S.R} (In windows console try pasting by right clicking).")  # fmt: skip
        print("3. If not using a log file, instead enter the ID list in this format: FirstID, SecondID, ThirdID, ... \n")  # fmt: skip
        data = str(input("Paste the list here, then hit Enter: "))  # fmt: skip
        if str(data).lower() == "x":
            return "MainMenu", None
        print("\n")  # fmt: skip

    # Parse data into list
    if manuallyEnter == False and "[" in data and "]" in data:
        matchBetweenBrackets = "(?<=\[)(.*?)(?=\])"  # Matches text between first set of two square brackets
        # matchIncludeBracktes = '\[(.*?)\]' # Matches between square brackets, including brackets
        resultList = str(re.search(matchBetweenBrackets, data).group(0))
    else:
        resultList = data
    resultList = resultList.replace("'", "")
    resultList = resultList.replace("[", "")
    resultList = resultList.replace("]", "")
    resultList = resultList.replace(" ", "")
    resultList = resultList.split(",")

    if len(resultList) == 0:
        print(f"\n{F.RED}Error Code R-1:{S.R} No comment IDs detected, try entering them manually and make sure they are formatted correctly.")  # fmt: skip
        input("\nPress Enter to return to main menu...")  # fmt: skip
        return "MainMenu", None

    # Check for valid comment IDs
    validCount = 0
    notValidCount = 0
    notValidList = []
    for id in resultList:
        if id[0:2] == "Ug":
            validCount += 1
        else:
            notValidCount += 1
            notValidList.append(id)

    if notValidCount > 0:
        print(f"{F.YELLOW}Possibly Invalid Comment IDs:{S.R} " + str(notValidList)+ "\n")  # fmt: skip

    if notValidCount == 0:
        print(f"\n{F.GREEN}Loaded all {str(validCount)} comment IDs successfully!{S.R}")  # fmt: skip
        input(f"\nPress Enter to begin {actionNoun}... ")  # fmt: skip
    elif validCount > 0 and notValidCount > 0:
        print(f"{F.RED}Warning!{S.R} {str(validCount)} valid comment IDs loaded successfully, but {str(notValidCount)} may be invalid. See them above.")  # fmt: skip
        input(f"\nPress Enter to try {actionNoun} anyway...\n")  # fmt: skip
    elif validCount == 0 and notValidCount > 0:
        print(f"\n{F.RED}Warning!{S.R} All loaded comment IDs appear to be invalid. See them above.")  # fmt: skip
        input(f"Press Enter to try {actionNoun} anyway...\n")  # fmt: skip
    if returnFileName == False:
        return resultList, None
    else:
        if listFileName:
            return resultList, pathlib.Path(os.path.relpath(listFileName)).stem
        else:
            return resultList, "Entered_List" + str(randrange(999))


######################################### Read & Write Dict to Pickle File #########################################
def write_dict_pickle_file(
    dictToWrite,
    fileName,
    relativeFolderPath=RESOURCES_FOLDER_NAME,
    forceOverwrite=False,
):

    fileNameWithPath = os.path.join(relativeFolderPath, fileName)

    success = False
    while success == False:
        if os.path.isdir(relativeFolderPath):
            success = True
        else:
            try:
                os.mkdir(relativeFolderPath)
                success = True
            except:
                print(f"Error: Could not create folder. Try creating the folder {relativeFolderPath} to continue.")  # fmt: skip
                input("Press Enter to try again...")  # fmt: skip

    if os.path.exists(fileNameWithPath):
        if forceOverwrite == False:
            print(f"\n File '{fileName}' already exists! Either overwrite, or you'll need to enter a new name.")  # fmt: skip
            if choice("Overwrite File?") == True:
                pass
            else:
                confirm = False
                while confirm == False:
                    newFileName = (
                        input("\nEnter a new file name, NOT including the extension: ")
                        + ".save"
                    )
                    print("\nNew file name: " + newFileName)  # fmt: skip
                    confirm = choice("Is this correct?")
                fileNameWithPath = os.path.join(relativeFolderPath, newFileName)

    success = False
    while success == False:
        try:
            with open(fileNameWithPath, "wb") as pickleFile:
                pickle.dump(dictToWrite, pickleFile)
                # json.dump(dictToWrite, jsonFile, indent=4)
            pickleFile.close()
            success = True
        except:
            traceback.print_exc()
            print("--------------------------------------------------------------------------------")  # fmt: skip
            print("Something went wrong when writing your pickle file. Did you open it or something?")  # fmt: skip
            input(f"\nPress Enter to try loading file again: {fileNameWithPath}")  # fmt: skip
    return True


def read_dict_pickle_file(fileNameNoPath, relativeFolderPath=RESOURCES_FOLDER_NAME):
    failedAttemptCount = 0
    fileNameWithPath = os.path.join(relativeFolderPath, fileNameNoPath)
    while True and not failedAttemptCount > 2:
        if os.path.exists(fileNameWithPath):

            failedAttemptCount = 0
            while True and not failedAttemptCount > 2:
                try:
                    with open(fileNameWithPath, "rb") as pickleFile:
                        # dictToRead = json.load(jsonFile)
                        dictToRead = pickle.load(pickleFile)
                    pickleFile.close()
                    return dictToRead

                except:
                    traceback.print_exc()
                    print("--------------------------------------------------------------------------------")  # fmt: skip
                    print("Something went wrong when reading your pickle file. Is it in use? Try closing it.")  # fmt: skip
                    input(f"\nPress Enter to try loading file again: {fileNameWithPath}")  # fmt: skip
                    failedAttemptCount += 1
            return False

        else:
            print(f"\nFile '{fileNameNoPath}' not found! Try entering the name manually.")  # fmt: skip
            input(f"\nPress Enter to try loading file again: {fileNameWithPath}")  # fmt: skip
            failedAttemptCount += 1

    return False


def try_remove_file(fileNameWithPath):
    attempts = 1
    while attempts < 3:
        try:
            os.remove(fileNameWithPath)
            return True
        except:
            print(f"\n{F.RED}\nERROR:{S.R} Could not remove file: '{fileNameWithPath}'. Is it open? If so, try closing it.")  # fmt: skip
            input("\nPress Enter to try again...")  # fmt: skip
            attempts += 1
    print(f"\n{F.RED}\nERROR:{S.R} The File '{fileNameWithPath}' still could not be removed. You may have to delete it yourself.")  # fmt: skip
    input("\nPress Enter to continue...")  # fmt: skip
    return False


def check_existing_save():
    relativeSaveDir = os.path.join(RESOURCES_FOLDER_NAME, "Removal_List_Progress")
    savesList = list()
    if os.path.isdir(relativeSaveDir):
        fileList = list()
        for (_, _, filenames) in os.walk(relativeSaveDir):
            fileList.extend(filenames)
        if len(fileList) > 0:
            for fileName in fileList:
                if fileName[-5:] == ".save":
                    savesList.extend([fileName])

    return savesList
