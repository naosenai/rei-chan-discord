import urllib.parse
import re

import requests as r
from bs4 import BeautifulSoup as bs


class Song:
    def __init__(self, query: str) -> None:
        self.input = query
        self.is_link = bool()
        self.query = self._query(query)

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
    
        self.links_found = self.__get_sites() if not self.is_link else None
        self.lyrics_found = self.__get_lyrics() if self.is_link else None


    def _query(self, query):
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


    def __get_sites(self) -> bool:
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


    def __get_lyrics(self) -> bool:
        self._request(self.query)
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

        self.__extract_image(rows)
        
        for label_row, row in zip(rows, rows[1:]):
            label = label_row.find('b')
            if label:
                label_text = label.get_text().strip()

                if label_text == "Song title":
                    self.__extract_title(row)
                elif label_text == "Original Upload Date":
                    self.__extract_date(row)
                elif label_text == "Singer":
                    self.__extract_singers(row)
                elif label_text == "Producer(s)":
                    self.__extract_producers(row)
                elif label_text == "Views":
                    self.__extract_views(row)
                elif label_text == "Links":
                    self.__extract_links(row)
                elif label_text == "Description":
                    self.__extract_description(row)
    
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
            style = row.get('style', '')

            for i, col in enumerate(cols):
                colspan = int(col.get('colspan', 1))

                while len(self.lyrics) < i + colspan:
                    self.lyrics.append("")

                if len(col.find_all('br')) > 0 and not col.get_text(strip=True):
                    for i in range(len(self.lyrics)):
                        self.lyrics[i] += "\n"
                else:
                    text = col.get_text()
                    text = self.apply_discord_formatting(text, style)
                    for j in range(colspan):
                        self.lyrics[i + j] += text

    def apply_discord_formatting(self, text: str, style: str) -> str:
        formatted_text = text.rstrip('\n')
        formatted_style = re.sub(r'\s*:\s*', ': ', re.sub(r';\s*', '; ', style))
        if 'font-family: monospace' in formatted_style:
            formatted_text = f"`{formatted_text}`"

        if 'font-style: italic' in formatted_style:
            formatted_text = f"*{formatted_text}*"

        if 'font-weight: bold' in formatted_style:
            formatted_text = f"**{formatted_text}**"

        if 'text-decoration: line-through' in formatted_style:
            formatted_text = f"~~{formatted_text}~~"

        if 'text-decoration: underline' in formatted_style:
            formatted_text = f"__{formatted_text}__"

        if text.endswith('\n'):
            formatted_text += '\n'
        return formatted_text

    def __extract_image(self, rows):
        first_td = rows[0].find('td')
        image_tag = first_td.find('img')
        if image_tag and image_tag.get('src'):
            self.image = image_tag['src']

    def __extract_title(self, row):
        self.title = row.find('b').get_text().strip()

    def __extract_date(self, row):
        self.date = row.get_text().replace('\xa0', ' ').strip()
        
    def __extract_singers(self, row):
        for singer in row.find_all('a'):
            self.singers.append(singer.get_text().strip())

    def __extract_producers(self, row): # this is a very, very shitty chatgpt solution. FIX THIS FR
        producer_text = row.get_text(separator="\n").strip()

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
            link_tag = row.find('a', string=producer_line)
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

    def __extract_views(self, row):
        self.views = row.get_text().strip()

    def __extract_links(self, row):
        for link in row.find_all('a'):
            href = link.get('href')
            title = link.get_text()
            self.links.append({'href': href, 'title': title})

    def __extract_description(self, row):
        description_content = row.find('div', class_='NavContent')
        if description_content:
            self.description = description_content.get_text().strip()