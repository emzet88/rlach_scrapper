# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import csv
import os
#import chardet
import re
from urllib.parse import urljoin
import pandas as pd
import traceback
import re
import logging

def format_date(date_str):
    day, month, year = date_str.split("-")
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"  # Zero-fill month and day for consistent format


def extract_number_before_pattern(text, pattern, start_position=0):
    """
    Function to find the first number before a given pattern in a string starting from a given position.
    
    :param text: The input string (e.g., zmiany string).
    :param pattern: The pattern to search for (e.g., 'XIV(B)').
    :param start_position: The position in the string from where to start the search. Default is 0 (beginning of the string).
    :return: The first number before the pattern, or None if not found.
    """
    # Slice the text starting from the start_position
    text_to_search = text[start_position:]
    
    # Regular expression to find the pattern with its preceding number
    regex = r'(\d+)[^\d]*' + re.escape(pattern)  # e.g., (\d+)-XIV\(B\)
    
    # Search for the pattern in the text starting from the given position
    match = re.search(regex, text_to_search)
    
    if match:
        # Return the number that precedes the given pattern
        return match.group(1)
    else:
        # Return None if no match is found
        return None

def determine_program_version(zmiany, heat_list_df):
    version = ''
    gate = ''
    rider = extract_number_before_pattern(zmiany, 'XV(A)')
    if rider is None:
        rider = extract_number_before_pattern(zmiany, 'XV(B)')
        if rider is None:
            rider = extract_number_before_pattern(zmiany, 'XV(C)')
            if rider is None:
                rider = extract_number_before_pattern(zmiany, 'XV(D)')
                gate = 4
            else:
                gate = 3
        else:
            gate = 2
    else:
        gate = 1
    
    #get heat 15 data
    heat_15_data = heat_list_df.iloc[14,gate].replace("najlepszy-","")

    if heat_15_data == 'red/yellow' or  heat_15_data =='blue/white':
        if int(rider) >=9:
            version = 'A'
        else:
            version = 'B'
    else:
        if int(rider) >=9:
            version = 'B'
        else:
            version = 'A'
    return version

        
def color_to_name(hex_color):
    color_map = {
        '#ffff00': 'yellow',
        '#ff0000': 'red',
        '#ffffff': 'white',
        '#0000ff': 'blue',
        '#c0c0c0': 'gray',
    }
    return color_map.get(hex_color.lower(), 'unknown')


def remove_xiv_xv_entries(zmiany):
    """
    Remove sections containing 'XIV' or 'XV' from the zmiany string.
    
    :param zmiany: The input string (e.g., zmiany string).
    :return: The modified string with sections containing 'XIV' or 'XV' removed.
    """
    # Pattern to match any substring like 'XIV(A)', 'XV(B)', etc.
    pattern = r'\b\d+-[A-Z]+\([A-D]\)(?:,)?'
    pattern_14 = r'XIV+\([A-D]\)(?:,)?'
    pattern_15 = r'XV+\([A-D]\)(?:,)?'
    
    # Substitute the matched patterns with an empty string
    cleaned_zmiany = re.sub(pattern, '', zmiany)
    cleaned_zmiany = re.sub(pattern_14, '', cleaned_zmiany)
    cleaned_zmiany = re.sub(pattern_15, '', cleaned_zmiany)
    # Remove extra commas, extra spaces, and clean up the string
    cleaned_zmiany = re.sub(r'\s*,\s*', ', ', cleaned_zmiany)  # Single space around commas
    cleaned_zmiany = re.sub(r'\s{2,}', ' ', cleaned_zmiany).strip()  # Trim multiple spaces
    cleaned_zmiany = re.sub(r',\s*$', '', cleaned_zmiany)  # Remove trailing comma if present
    
    return cleaned_zmiany

def roman_to_int(roman):
    """
    Convert a Roman numeral to an integer.
    
    :param roman: A string representing the Roman numeral (e.g., 'XIV')
    :return: The integer value of the Roman numeral (e.g., 14)
    """
    # Dictionary mapping Roman numerals to their values
    roman_values = {
        'I': 1, 'V': 5, 'X': 10, 'L': 50,
        'C': 100, 'D': 500, 'M': 1000
    }
    
    total = 0
    prev_value = 0
    
    # Loop through each character in the Roman numeral from right to left
    for char in reversed(roman):
        value = roman_values[char]
        # If the current value is less than the previous, subtract it; otherwise, add it
        if value < prev_value:
            total -= value
        else:
            total += value
        prev_value = value
    
    return total

def number_to_letter(number):
    """
    Convert a number to its corresponding letter (1 -> a, 2 -> b, etc.).
    
    :param number: The number to convert (1 -> a, 2 -> b, etc.)
    :return: The corresponding letter as a string.
    """
    # Dictionary to map numbers to letters
    number_to_letter_map = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}
    
    # Return the corresponding letter or None if the number is not in the map
    return number_to_letter_map.get(number, None)   

def int_to_roman(num):
    """
    Convert an integer to its Roman numeral representation.
    
    :param num: The integer to convert.
    :return: The Roman numeral representation as a string.
    """
    # Mapping of integer values to Roman numeral symbols
    roman_numerals = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I")
    ]
    
    roman = ""
    
    # Loop through the roman_numerals list and build the Roman numeral string
    for value, symbol in roman_numerals:
        while num >= value:
            roman += symbol
            num -= value
    
    return roman

def find_nth_occurrence(text, substring, n):
    position = -1
    for _ in range(n):
        position = text.find(substring, position + 1)
        if position == -1:
            return -1  # Return -1 if the n-th occurrence is not found
    return position


#folder
os.chdir("")

#logfile
logging.basicConfig(filename='rlach_scraping.log', level=logging.INFO, format='%(asctime)s - %(message)s')

year = '2018'

teams = ['LESZ.',  'WROC.',  'GORZ.',  'ZG.',  'CZĘS.',  'GRUD.',  'TORUŃ',  'TARN.']
for home_team in teams:
    for away_team in teams:
        if home_team != away_team: 
            try:

                # URL strony, z którą chcemy się połączyć - TODO ADD LOOP
                #url = 'http://www.speedwayw.pl/dmp/2018/togo_1.htm'
                url = 'http://www.speedwayw.pl/dmp/'+year+'/'+home_team.lower()[:2]+away_team.lower()[:2]+'_1.htm'

                #try:
                print("Rozpoczynam pobieranie zawartości strony...")

                # Pobieranie zawartości strony
                response = requests.get(url)
                response.raise_for_status()  # Sprawdza, czy żądanie się powiodło
                print("Strona została pomyślnie pobrana.")

                response.encoding = 'iso-8859-2'

                # Decode the raw HTML content based on the detected encoding
                html_content = response.text

                # Parsowanie HTML
                soup = BeautifulSoup(html_content, 'html.parser')

                # Extract the title of the meeting from the <title> tag or elsewhere if relevant
                title = soup.find("title").get_text(strip=True) if soup.find("title") else "NoTitle"

                # Find the date of the meeting within the text using regex
                # Assuming date format in text is DD-MM-YYYY or similar
                date_match = re.search(r"\d{1,2}-\d{1,2}-\d{4}", html_content)
                meeting_date = format_date(date_match.group(0)) if date_match else "NoDate"

                # Find the specific section of interest using the tag <tt> within the <blockquote>
                data_section = soup.find("blockquote").get_text()

                # Split the data into rows based on line breaks and remove empty lines
                rows = [line.strip() for line in data_section.split("\n") if line.strip()]

                output_csv = f"{title}_{meeting_date}.csv" 

                # Zapis do pliku CSV
                print(f'Zapisuję dane do pliku {output_csv}...')    

                with open(output_csv, mode="w", newline="", encoding="utf-8") as file:
                    writer = csv.writer(file)

                    # Write header
                    writer.writerow(["Position", "Rider", "Points", "1","2","3","4","5","6","7"])
                    riders_data = []

                    cnt = 0
                    
                    # Process each line of results to extract data
                    for row in rows[1:]:  # Skip the header line 
                        if row.strip():
                            # Skip lines that contain only time (e.g., "60:31")
                            if len(row.split()) == 1 and row.strip().count(':') == 1:
                                continue
                        # Use regular expressions to match parts of the line
                            if row.lower().startswith("sędzia"): #or row.lower().startswith("zmiany") :
                                #writer.writerow([row])  
                                break   
                            parts = row.split()
                        
                            # Parse line parts based on observed structure
                            position = parts[0]                            
                            if len(parts) > 5:                                           # Rider's number
                                name   = parts[1] + (" " + parts[2]  )  # Handle last names with a space
                                points = parts[3]                       # Rider's points
                            else:  
                                name   = parts[1]                       # Handle last names with a space
                                points = parts[2]                       # Rider's points
                            if parts[1] == 'brak' and parts[2] == 'zawodnika':
                                name = 'brak zawodnika'  
                                points = None
                            if points == "ns":                          # Rider's score details (e.g., (1,0,0))
                                scores = "()"
                            elif len(parts) > 5:
                                scores = parts[4] 
                            elif name == 'brak zawodnika': 
                                scores = None 
                            else:    
                                scores = parts[3]   

                            if name != 'brak zawodnika':
                                point_values = scores.strip('()').split(',')
                                            
                            #time = parts[-1]                                             

                            # Write each rider's data to the CSV
                            writer.writerow([position, name, points] + point_values)
                            riders_data.append([position, name, points] + point_values)

                            if cnt < len([position, name, points] + point_values):
                                cnt = len([position, name, points] + point_values)

                            column_list = ["Number", "Rider", "Points", "1","2","3","4","5","6","7"]

                            #remove unnecessary headers
                            column_list = column_list[0:cnt]


                            riders_data_df = pd.DataFrame(riders_data, columns = column_list)

                print(f'The results have been saved to {output_csv}.')

                #match details  

                zmiany_text = ""
                zmiany_found = False

                # Meeting details dictionary
                meeting_details = {
                        "Sędzia": None,
                        "Data": meeting_date,
                        "Zmiany": None
                    } 
                lines = soup.get_text().split("\n")

                for i, line in enumerate(lines):
                    line = line.strip()

                    if line.lower().startswith("sędzia:"):
                        # Extract the judge's name following "sędzia:"
                        sedzia_text = line.split(":", 1)[1].strip()
                        sedzia_name_match = re.search(r"([A-Za-z]+ [A-Za-z]+)", sedzia_text)
                        meeting_details["Sędzia"] = sedzia_name_match.group(0) if sedzia_name_match else sedzia_text
                        
                    elif "zmiany" in line.lower():
                        # Extract changes following "zmiany:"
                            zmiany_found = True
                            #zmiany_text += line + " " 

                            # Process the next two lines (that should contain the zmiany data)
                            if i + 1 < len(lines):
                                zmiany_text += lines[i + 1].strip() + " "
                            if i + 2 < len(lines):
                                zmiany_text += lines[i + 2].strip()
                    
                            break

                zmiany_cleaned = zmiany_text.replace("<br>", " ").strip()
                meeting_details["Zmiany"] = zmiany_cleaned 

                # You can print to verify if zmiany_cleaned looks correct
                print("Zmiany Text:\n", zmiany_cleaned)

                #tabela biegów processing:        

                tabela_link_tag = soup.find("a", string=re.compile("tabela biegów", re.IGNORECASE))
                if tabela_link_tag and tabela_link_tag.get("href"):
                    tabela_link = tabela_link_tag["href"]
                    tabela_url = urljoin(url, tabela_link) # Construct full URL

                    # Step 3: Fetch the "tabela biegów" page content
                    tabela_response = requests.get(tabela_url)
                    tabela_response.encoding = 'iso-8859-2'  # Set encoding

                    if tabela_response.status_code == 200:
                        tabela_soup = BeautifulSoup(tabela_response.text, "html.parser")

                        # Step 4: Locate the table and extract rows (assuming a <table> element is present)
                        tables = tabela_soup.find_all("table")
                        
                        if tables[1]:
                            riders_list_df = riders_data_df[['Number', 'Rider']]
                            heat_list = []

                            # A flag to check if we've written headers yet
                            headers_written = False

                            table = tables[1]
                            rows = table.find_all("tr")
                            # If headers have not been written yet, write the first table's header
                            if not headers_written:
                                headers = rows[0].find_all("th")
                                if headers:
                                    writer.writerow([header.get_text(strip=True) for header in headers])
                                    headers_written = True

                                    # Write the data rows
                                for row in rows[1:]:  # Skip the first row if it's the header
                                    columns = row.find_all("td")
                                    row_data = []
                                    # First column: extract the number followed by a semicolon
                                    first_column = columns[0].get_text(strip=True) 
                                    row_data.append(first_column.replace(".",""))
                                    
                                    # Process the remaining columns
                                    for column in columns[1:]:
                                        # Extract all <font> elements inside the column
                                        font_tags = column.find_all('font', color=True)
                                        color_text_pairs = []
                                        
                                        for font_tag in font_tags:
                                            text = font_tag.get_text(strip=True)
                                            color = font_tag['color']
                                            color_name = color_to_name(color)  # Convert hex color to name
                                            color_text_pairs.append(f'{text}-{color_name}')  # Combine text and color name
                                        
                                        # Join all the text-color pairs with a slash (/) and append to row data
                                        row_data.append('/'.join(color_text_pairs))
                                        heat_list.append(row_data)

                            #print(heat_list)                            

                            heat_list_df = pd.DataFrame(heat_list, columns = ['heat_number', 'gate A', 'gate B', 'gate C', 'gate D' ])
                            heat_list_df['heat_number'] = heat_list_df['heat_number'].astype(int) 
                            heat_list_df = heat_list_df.groupby('heat_number').agg(lambda x: ' / '.join(x.unique())).reset_index().sort_values(by = 'heat_number', ascending = True)
                            


                            #determine program version

                            print(heat_list_df)

                            version = determine_program_version(zmiany_cleaned, heat_list_df)

                            print(version)

                            if version == 'A':
                                heat_list_df["gate A"] = heat_list_df["gate A"].str.split('/').str[0]
                                heat_list_df["gate B"] = heat_list_df["gate B"].str.split('/').str[0]
                                heat_list_df["gate C"] = heat_list_df["gate C"].str.split('/').str[0]
                                heat_list_df["gate D"] = heat_list_df["gate D"].str.split('/').str[0]
                            elif version =='B':
                                heat_list_df["gate A"] = heat_list_df["gate A"].str.split('/').str[1]
                                heat_list_df["gate B"] = heat_list_df["gate B"].str.split('/').str[1]
                                heat_list_df["gate C"] = heat_list_df["gate C"].str.split('/').str[1]
                                heat_list_df["gate D"] = heat_list_df["gate D"].str.split('/').str[1]    
                            else:
                                print("version incorrect")

                                exit(0)     

                
                            #biegi nominowane
                            for n in range (13,15):
                                for k in range(1,5):
                                    if n == 13:
                                        tekst = "nominowany"
                                    elif n==14:
                                        tekst = "najlepszy"
                                    heat_list_df.iloc[n,k]  = heat_list_df.iloc[n,k].replace(tekst,str(extract_number_before_pattern(zmiany_cleaned, int_to_roman(n+1)+"("+number_to_letter(k)+")")) )  
                                    print(int_to_roman(n+1)+"("+number_to_letter(k)+")")
                                    print(str(extract_number_before_pattern(zmiany_cleaned, int_to_roman(n+1)+"("+number_to_letter(k)+")")))
                                    if extract_number_before_pattern(zmiany_cleaned, int_to_roman(n+1)+"("+number_to_letter(k)+")") is None:
                                        logging.info(f"None value in heat {n+1}, match {title}, {date_match} ")
                        
                            
                            #apply changes
                            print(zmiany_cleaned)
                            zmiany_zas = remove_xiv_xv_entries(zmiany_cleaned)
                            print(zmiany_zas)



                            #loop

                            '''        riders_scores_df = riders_data_df.drop('Points', axis = 1)
                            print(riders_scores_df)

                            def get_rider_score(rider_name):
                            # Get the rider row by name
                                rider_row = riders_scores_df[riders_scores_df['Rider'] == rider_name]
                        
                                if not rider_row.empty:
                                    # Return the first score for this rider
                                    return rider_row.iloc[0, 2]  # score1 is in column index 2
                                else:
                                    # Return None if the rider is not found
                                    return None
                                
                            def remove_and_shift(rider_name):
                                # Find the row where the rider name matches
                                rider_row = riders_scores_df[riders_scores_df['Rider'] == rider_name]
                                
                                if not rider_row.empty:
                                    # Get the column index range excluding 'Number' and 'Rider'
                                    cols = riders_scores_df.columns[2:]
                                    
                                    # Find the first non-None value and remove it (replace with None)
                                    for col in cols:
                                        if pd.notna(rider_row.iloc[0][col]):
                                            riders_scores_df.loc[riders_scores_df['Rider'] == rider_name, col] = None
                                            break
                                    
                                    # Shift remaining values to the left
                                    for i in range(2, len(cols)):  # Start from the third column (index 2)
                                        riders_scores_df.loc[riders_scores_df['Rider'] == rider_name, cols[i-1]] = riders_scores_df.loc[riders_scores_df['Rider'] == rider_name, cols[i]]
                                    
                                    # Set the last column to None after shifting
                                    riders_scores_df.loc[riders_scores_df['Rider'] == rider_name, cols[-1]] = None

                            for h in range(1,16):
                                #check if there were changes
                                rom = int_to_roman(h)
                                replacement = extract_number_before_pattern(zmiany_zas,rom)
                                if replacement is not None: 
                                    if replacement < 9:
                                        #check if hometeam rider has been replaced
                                    replacement_2 = extract_number_before_pattern(zmiany_zas,rom, zmiany_cleaned.find(rom)+1)
                                    if replacement_2 is not None: 
                                        replacement_3 = extract_number_before_pattern(zmiany_zas,rom, find_nth_occurrence(zmiany_cleaned, rom, 2)+1)
                                        if replacement_3 is not None: 
                                            replacement_4 = extract_number_before_pattern(zmiany_zas,rom, find_nth_occurrence(zmiany_cleaned, rom, 3)+1)'''



                            #Find heats with changes

                            #find riders that were substituted
                            
                            #apply changes

                            #REPLACE NUMBERS WITH NAMES
                            name_dict = pd.Series(riders_list_df.Rider.values, index=riders_list_df.Number.astype(str)).to_dict()

                            def replace_number_with_name(value):
                                number, color = value.split('-')
                                name = name_dict.get(number, number)  # Get the name, or the number itself if not found
                                return f"{name} - {color}"  


                            for col in ['gate A', 'gate B', 'gate C', 'gate D']:
                                heat_list_df[col] = heat_list_df[col].apply(replace_number_with_name)
                                #split columns     
                                heat_list_df[[col+" rider", col+" helmet"]] = heat_list_df[col].str.split(' - ', expand = True)  
                                heat_list_df.drop(col,axis=1, inplace=True) 
                                                            
                            
                            # move it further to save the corrected data
                            # Construct output CSV filename
                            output_csv = f"{title}_{meeting_date}_szczegóły_meczu.csv"

                            # Step 5: Save table rows to CSV
                            with open(output_csv, mode="w", newline="", encoding="utf-8-sig") as file:
                                writer = csv.writer(file, quoting=csv.QUOTE_MINIMAL)

                                #save match details
                                writer.writerow([title])
                                for key, value in meeting_details.items():
                                    writer.writerow([f"{key}: {value}"])

                                #save riders list
                                riders_list = [riders_list_df.columns.to_list()] + riders_list_df.values.tolist()
                                writer.writerows(riders_list)

                                #save heat list
                                writer.writerow(["Heat list"])
                                heat_list = [heat_list_df.columns.to_list()] + heat_list_df.values.tolist()
                                writer.writerows(heat_list)

                                # Loop through each table and save it
                                '''for table in tables:
                                    rows = table.find_all("tr")
                                    # If headers have not been written yet, write the first table's header
                                    if not headers_written:
                                        headers = rows[0].find_all("th")
                                        if headers:
                                            writer.writerow([header.get_text(strip=True) for header in headers])
                                        headers_written = True

                                    # Write the data rows
                                    for row in rows[1:]:  # Skip the first row if it's the header
                                        columns = row.find_all("td")
                                        if columns:  # Only write rows that have data
                                            writer.writerow([column.get_text(strip=True) for column in columns])'''

                            print(f"Tabela biegów data has been saved to '{output_csv}'.")
                        else:
                            print("No table found on the tabela biegów page.")
                    else:
                        print(f"Failed to retrieve the tabela biegów page. Status code: {tabela_response.status_code}")
                else:
                    print("No link to 'tabela biegów' found on the main page.")
                    
                
            
            except requests.exceptions.HTTPError as http_err:
                logging.info(f" URL: {url}. Błąd HTTP: {http_err}")
                print(f" URL: {url}.Błąd HTTP: {http_err}")
                continue
            except requests.exceptions.RequestException as req_err:
                logging.info(f" URL: {url}.Błąd połączenia: {req_err}")
                print(f" URL: {url}.Błąd połączenia: {req_err}")
                continue
            except Exception as err:
                logging.info(f" URL: {url}.Wystąpił nieoczekiwany błąd: {err} " + str(traceback.extract_stack()[-1][1]))
                print(f" URL: {url}.Wystąpił nieoczekiwany błąd: {err} " + str(traceback.extract_stack()[-1][1]))
