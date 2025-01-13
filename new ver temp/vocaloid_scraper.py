import urllib.parse

import requests as r
from bs4 import BeautifulSoup as bs


class Song:
  def __init__(self) -> None:
    self.input = []
    self.is_link = bool()
    self.query = ""

    self.content = ""
    self.error_message = ""

    self.image = ""
    self.title = ""
    self.date = ""
    self.singers = []
    self.producers = []
    self.views = ""
    self.links = []
    self.description = ""
    self.lyrics = []

    self.search_found = bool()
    self.disambiguation_found = bool()
    self.lyrics_found = bool()
    self.info_found = bool()
  

def initialize(self, query: str, expected_output: str = None):
  if not expected_output or expected_output not in {'search', 'song', 'disam'}:
    self._query(query)
  elif expected_output != 'search':
    self.is_link = True



  def _query(self, query: str):
    parsed = urllib.parse.urlparse(query)
    self.is_link = bool(parsed.scheme) and bool(parsed.netloc)
    return query if self.is_link else urllib.parse.quote(query)


  def _request(self, url: str) -> object|None:
    try:
      response = r.get(url)
      response.raise_for_status()
      data = bs(response.content, 'html.parser')
      self.content = data
    except r.exceptions.RequestException as e:
      self.error_message = e
      return None


  def __get_pages(self) -> bool:
    search_link = f"https://vocaloidlyrics.fandom.com/wiki/Special:Search?query={self.query}"
    self._request(search_link)
    if not self.content:
      return False
    res = self.content.find('ul', class_='unified-search__results')
    if not res:
      self.error_message = "No Matching Results"
      return False
    links = res.find_all('a', class_='unified-search__result__title')
    for link in links:
      href = link.get('href')
      title = link.get('data-title')
      self.links.append({'href': href, 'title': title})
    
    return True
  
  def __get_disambiguation(self) -> bool:
    ''


  def __get_lyrics(self) -> bool:
    if not self.content:
      return False
    try:
      disambiguation_res = self.content.find('div', class_="mbox notice hidden")
      mono_res = self.content.find('div', class_="poem")
      multi_res = self.content.find('table', style='width:100%')
    except Exception as e:
      self.error_message = f"Error finding content: {e}"
      return False
    try:
      if disambiguation_res:
        self.__extract_disambiguation()
      elif multi_res:
        self.__extract_multi_lyrics(multi_res)
        self.__set_info() 
      elif mono_res:
        self.__extract_mono_lyrics(mono_res)
        self.__set_info()
      else:
        raise
    except Exception as e:
      self.error_message = f"Missing or broken lyrics: {e}"
      return False
    return True
  
  def __set_info(self) -> bool:
    rows = self.content.find('center').find_all('tr')

    self.extract_image(rows)
    
    i = 0
    while i < len(rows):
      row = rows[i]
      label = row.find('b')
      if label:
        label_text = label.get_text().strip()

        if label_text == "Song title":
            self.__extract_title(rows, i)
        elif label_text == "Original Upload Date":
            self.__extract_date(rows, i)
        elif label_text == "Singer":
            self.__extract_singers(rows, i)
        elif label_text == "Producer(s)":
            self.__extract_producers(rows, i)
        elif label_text == "Views":
            self.__extract_views(rows, i)
        elif label_text == "Links":
            self.__extract_links(rows, i)
        elif label_text == "Description":
            self.__extract_description(rows, i)

      i += 1  # Move to the next row
    return True
  
  def __extract_disambiguation(self) -> None:
    res = self.content.find('div', class_='mw-parser-output')
    lines = res.find_all('li')
    for line in lines:
      href = line.find('a').get('href')
      title = line.get_text()
      self.links.append({'href': href, 'title': title})

  def __extract_mono_lyrics(self, lyrics) -> None:
    self.lyrics.append(lyrics.find('p').get_text())

  def __extract_multi_lyrics(self, lyrics) -> None:
    rows = lyrics.tbody.findAll('tr')
    for row in rows:
      cols = row.findAll('td')
      for i, col in enumerate(cols):
        colspan = int(col.get('colspan', 1))
        text = col.get_text()
        while len(self.lyrics) < i + colspan:
          self.lyrics.append("")
        for j in range(colspan):
          self.lyrics[i + j] += text

  def extract_image(self, rows):
    first_td = rows[0].find('td')
    image_tag = first_td.find('img')
    if image_tag and image_tag.get('src'):
      self.image = image_tag['src']

  def __extract_title(self, rows, index):
    self.title = rows[index + 1].find('b').get_text().strip()

  def __extract_date(self, rows, index):
    date_td = rows[index + 1]
    self.date = date_td.get_text().replace('\xa0', ' ').strip()
      
  def __extract_singers(self, rows, index):
    singer_td = rows[index + 1]
    for singer in singer_td.find_all('a'):
      self.singers.append(singer.get_text().strip())

  def __extract_producers(self, rows, index): # this is a very, very shitty chatgpt solution. FIX THIS FR
    producer_td = rows[index + 1]
    producer_text = producer_td.get_text(separator="\n").strip()

    # Split the text by newlines (each line represents a producer group)
    producers_data = producer_text.split("\n")
    # Dictionary to track producers and their roles
    producers_dict = {}

    # Loop over each line (producer group) and process it
    for producer_line in producers_data:
        producer_line = producer_line.strip()
        if not producer_line:
            continue
        
        name = None
        role = None
        link = None

        # Find the link if it exists (this indicates a named link)
        link_tag = producer_td.find('a', string=producer_line)
        if link_tag:
            name = link_tag.get_text().strip()
            link = link_tag.get('href')
            producer_line = producer_line.replace(name, "").strip()

        # If the remaining text contains a role in parentheses, extract it
        if '(' in producer_line and ')' in producer_line:
            role = producer_line.split('(')[1].split(')')[0].strip()
            name = producer_line.split('(')[0].strip() if not name else name

        # Skip if no name (neither a link nor a valid role)
        if not name:
            continue

        # Handle multiple names listed in one line (e.g., "Mera Shiroki, nakuri")
        names = [n.strip() for n in name.split(',')] if ',' in name else [name]

        # Add to producers_dict under the correct role
        if role not in producers_dict:
            producers_dict[role] = {'names': [], 'link': link}
        producers_dict[role]['names'].extend(names)

    # Final list of producers (flatten the role-names structure)
    self.producers = [
        {'name': name, 'role': role, 'link': data['link']}
        for role, data in producers_dict.items()
        for name in data['names']
    ]

  def __extract_views(self, rows, index):
    self.views = rows[index + 1].get_text().strip()

  def __extract_links(self, rows, index):
    link_td = rows[index + 1]
    for link in link_td.find_all('a'):
      href = link.get('href')
      title = link.get_text()
      self.links.append({'href': href, 'title': title})

  def __extract_description(self, rows, index):
    description_content = rows[index + 1].find('div', class_='NavContent')
    if description_content:
      self.description = description_content.get_text().strip()