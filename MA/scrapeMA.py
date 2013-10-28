##
# MA scraping code for MBB project
# scrapes the MA board of library commissioners website for info 
# UROP by rileyb [at] mit; supervised by petey [at] mit
# writeup: http://civic.mit.edu/node/4451
##

import re
import urllib
import urllib2

from bs4 import BeautifulSoup

FIRST_TOWN = "Abington"
FILE = "MA.csv"
FILE_WITH_TYPES = "MA_libraries_2013.csv"

def getRequestToSoup(url):
    response = urllib2.urlopen(url)
    return BeautifulSoup(response.read())

def postRequestToSoup(url, data):
    response = urllib2.urlopen(url, data)
    return BeautifulSoup(response.read())

def findLibraryRows(soup):
    tables = soup.find_all("table") # There are a few tables in the soup...
    librariesTable = tables[len(tables)-1] # But the libraries are in the last one
    allRows = librariesTable.find_all("tr")
    libraryRowList = []
    for row in allRows:
        if len(row.find_all("td")) > 0: # Don't care about header, etc. rows
            libraryRowList.append(row)
    return libraryRowList

def getLibraryLinkFromRow(row):
    cells = row.find_all("td") # Look at columns/cells within each row
    for cell in cells: # Each row has a few columns/cells...
        if cell.a: # But we only care about the cell with the link
            return cell.a["href"]

def getFieldValue(thLine):
    return thLine.parent.find_all("td")[0].text

def makeFile():
    # Clear file
    f = open(FILE, 'w')
    f.close()

    # Load file with lbrary types, stick in a list
    fileWithTypes = open(FILE_WITH_TYPES, 'r')
    fileWithTypesList = fileWithTypes.readlines()
    fileWithTypes.close()

    # Load search webpage
    searchSoup = getRequestToSoup("http://mblc.state.ma.us/libraries/directory/index.php")

    # Get list of municipalities to search for
    municipalitiesHTML = searchSoup.find_all("option") # Municipalities all in option tags in dropdown menu

    # For each municipality...
    for municipalityHTML in municipalitiesHTML:
        primaryEmails = []
        print municipalityHTML["value"]
        municipalityValue = municipalityHTML["value"]
        # Open file appropriately, initialize string to add to CSV file
        if municipalityValue == FIRST_TOWN: # First time, open to write
            municipalityDataString = "Municipality;Name;Library Type;Address Line 1;Address Line 2;City;Zip;Phone;Fax;Library Email;First Listed Staff Member;Staff Email;\t\t\t\t\t;Primary Email;Repeat Contact?;Cc Email;Use Fax;Use Mail;Status;\t\t\t\t\t;Website (some links broken)\n"
        else: # After the second town, don't keep opening, just append
            municipalityDataString = ""

        # Submit search
        if len(municipalityValue) > 0:
            searchValue = urllib.urlencode({ 'municipality' : municipalityValue })
            resultsSoup = postRequestToSoup("http://mblc.state.ma.us/cgi-bin/ldap_search.pl", searchValue)

            # Get list of libraries in municipality
            libraryRows = findLibraryRows(resultsSoup)
            for row in libraryRows:
                libraryLink = getLibraryLinkFromRow(row)
                # Get library page
                librarySoup = getRequestToSoup("http://mblc.state.ma.us" + libraryLink)
                # Extract relevant fields   
                # Define different relevant subsets of the HTML to find fields in
                pSoup = librarySoup.find_all("p")
                h3Soup = librarySoup.find("h3")
                thSoup = librarySoup.find_all("th")
                importantSoup = librarySoup.find_all("div","important")
                # Initialize fields
                municipality, name, type, addressLine1, addressLine2, city, zip, phone,\
                    fax, email, staff, staffEmail, primaryEmail, repeat, ccEmail,\
                    useFax, useMail, status, website, blank = "","","","","","","","","","","","","","","","","","","",""
                # Set blank to tab character
                blank = "\t\t\t\t\t"
                # Find municipality name in pSoup. There are two p tags, so it's a little harder.
                for pLine in pSoup:
                    if "Municipality" in pLine.strong.text: # Tag for field name is strong
                        municipality = pLine.a.text # Municipality name is second element
                        break
                # Find name in h3Soup. There's only one h3 tag, so this is relatively straightforward.
                brSpot = h3Soup.find("br") # The name comes on two lines...
                organization = brSpot.previousSibling 
                library = brSpot.nextSibling
                if organization in library:
                    name = library
                else:
                    name = organization + " " + library
                # Find a bunch of fields in thSoup. There's a th tag for most of the field headers
                for thLine in thSoup:
                    thText = thLine.text
                    if "Address" in thText:
                        brSpots = thLine.parent.find_all("td")[0].find_all("br")
                        addressLine1 = brSpots[0].previousSibling.replace("\n","")
                        if len(brSpots) == 1:
                            cityZipList = brSpots[0].nextSibling.split(u"\xa0\xa0")
                        else:
                            addressLine2 = brSpots[0].nextSibling.replace("\n","")
                            cityZipList = brSpots[1].nextSibling.split(u"\xa0\xa0")
                        city = cityZipList[0].encode('utf-8').replace("\n","").replace("Massachusetts", "MA").replace("Ma", "MA")
                        try:
                            zip = cityZipList[1].encode('utf-8').replace("\n","")
                        except IndexError:
                            pass
                    elif "Phone" in thText:
                        phone = getFieldValue(thLine)
                        if phone[5] != " ":
                            phone = phone[:5] + " " + phone[5:]
                    elif "Fax" in thText:
                        fax = getFieldValue(thLine)
                        if fax[5] != " ":
                            fax = fax[:5] + " " + fax[5:]
                    elif "Email" in thText:
                        email = getFieldValue(thLine)
                    elif "Library Staff" in thText:
                        # Just first staff member
                        parent = thLine.parent
                        staffHTML = thLine.parent.find("li")
                        if staffHTML != None: # Otherwise there's no staff listed
                            staff = staffHTML.a.text.replace("  "," ")
                            if "vacant" in staff or "--" in staff:
                                staff = ""
                            staffEmailLink = staffHTML.a["href"]
                            staffSoup = getRequestToSoup("http://mblc.state.ma.us" + staffEmailLink)
                            tdSoup = staffSoup.find_all("td")
                            for tdLine in tdSoup:
                                if tdLine.a != None:
                                    if "mailto" in tdLine.a["href"]:
                                        staffEmail = tdLine.a["href"].replace("mailto:","").replace(" ","")
                    elif "Web Site" in thText:
                        website = getFieldValue(thLine)
                # Check importantSoup to identify libraries that are former members 
                for importantLine in importantSoup:
                    if "Former" in importantLine.text:
                        status = "Former"
                        break
                if len(importantSoup) == 0:
                    status = "Active"
                # Establish primary and Cc emails
                if staffEmail != "":
                    primaryEmail = staffEmail
                    if email != "" and email != primaryEmail:
                        ccEmail = email
                elif email != "":
                    primaryEmail = email
                elif fax != "":
                    useFax = fax
                else:
                    useMail = "See address info"

                if primaryEmail != "":
                    # Check for repeated primary emails
                    if primaryEmail in primaryEmails:
                        repeat = "REPEAT"
                    # Add primary email to primary emails list
                    primaryEmails.append(primaryEmail)

                # Figure out what type of library this is
                typeMap = {"Academic": "College/Univ.",
                           "Public": "Public",
                           "School": "School: Unspecified",
                           "School-PHS":"High School: Public",
                           "School-PMES":"Elementary/Middle School: Public",
                           "School-PrHS":"High School: Private or Public Charter",
                           "School-PrMES":"Elementary/Middle School: Private or Public Charter",
                           "Special":"Special",
                           "Special-Corporate":"Corporate",
                           "Special-Institutional":"Grab-bag Institution",
                           "Special-Law":"Law-related (Court, Law Firm)",
                           "Special-Medical": "Medical"}
                for line in fileWithTypesList:
                    if organization in line and library in line:
                        typeFromFile = line.split(",")[1].replace("\"","")
                        type = typeMap[typeFromFile]
                        break
                # Add fields to data string, semicolon delimited
                municipalityDataString += "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s\n"\
                    %(municipality,
                      name,
                      type,
                      addressLine1,
                      addressLine2,
                      city,
                      zip,
                      phone,
                      fax,
                      email,
                      staff,
                      staffEmail,
                      blank,
                      primaryEmail,
                      repeat,
                      ccEmail,
                      useFax,
                      useMail,
                      status,
                      blank,
                      website)
        # Append libraries from this municipality to file
        f = open(FILE, 'a')
        try:
            f.write(municipalityDataString.encode('utf-8'))
        except UnicodeEncodeError:
            pass
        f.close()

makeFile()

