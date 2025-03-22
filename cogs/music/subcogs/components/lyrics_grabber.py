import requests
import re

# This is the updated version of the vocaloid_scraper.py file. Not yet implemented, but fully functional. 
# I highly recommend using this over the fuckery in the last file, if you choose to do so.

class SongInfo():
    def __init__(self):
        self.wiki_url = "https://vocaloidlyrics.fandom.com"

        self.query_input = None
        self.query_results = None

        self.page_input = None
        self.page_title = None
        self.page_content_warning = None
        self.page_image = None
        self.page_date = None
        self.page_singers = None
        self.page_producers = None
        self.page_views = None
        self.page_links = None
        self.page_extra_links = None
        self.page_description = None
        self.page_lyrics = None

    def get_query(self, query):
        self.query_input = query
        api_url = f"{self.wiki_url}/api.php?action=query&list=search&srsearch={query}&format=json"
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            search_results = data['query']['search']
            if search_results:
                self.query_results = []
                for page in search_results:
                    self.query_results.append((page['title'], f"{self.wiki_url}/wiki/{page['title'].replace(' ', '_')}"))
                return False
            else:
                return "Failed to discover results for '{self.page_query}'."
        else:
            return "Failed to retrieve content", response.status_code

    def get_page(self, title):
        self.page_input = title
        api_url = f"{self.wiki_url}/api.php?action=query&prop=revisions&rvprop=content&titles={title}&format=json"
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            pages = data['query']['pages']
            for _, page_data in pages.items():
                self.page_title = page_data['title']
                revisions = page_data.get('revisions', [])
                if revisions:
                    content = revisions[0].get('*', 'No content available.')
                    #print(content)

                    self.page_content_warning = self.extract_content_warning(content)
                    self.page_image = self.extract_image(content)
                    self.page_description = self.extract_description(content)
                    self.page_lyrics = self.extract_lyrics(content)
                    self.page_date = self.extract_date(content)
                    self.page_singers = self.extract_singers(content)
                    self.page_producers = self.extract_producers(content)
                    self.page_views = self.extract_views(content)
                    self.page_links = self.extract_links(content)
                    self.page_extra_links = self.extract_extra_links(content)

                    return False
                else:
                    return "Failed to access content for '{self.page_title}'."
        else:
            return "Failed to retrieve content", response.status_code
        
    def extract_description(self, content):
        match = re.search(r"\|description\s*=\s*(.*?)\n", content, re.DOTALL)
        return match.group(1).strip() if match else False

    def extract_image(self, content):
        match = re.search(r"\|image\s*=\s*(.*?)\n", content, re.DOTALL)
        if match:
            return f"{self.wiki_url}/wiki/File:{match.group(1).replace(' ', '_')}"
        return False

    def extract_lyrics(self, content):
        lyrics_block = re.search(r'==Lyrics==\s*(.*?)(\n\s*\n|\Z)', content, re.DOTALL).group(1)
        tabber_block = re.search(r'<tabber>(.*?)</tabber>', lyrics_block, re.DOTALL)
        tabs = tabber_block.group(1).split('|-|') if tabber_block else [lyrics_block]
        lyrics = {}

        for tab_content in tabs:
            tab_name_match = re.search(r'\n(.*?)\s*=', tab_content)
            tab_name = tab_name_match.group(1) if tab_name_match else 'Untitled'

            columns_match = re.search(r'\{\| style="width:100%"\s*(.*?)\|-', tab_content, re.DOTALL)
            column_names = ['Original']
            if columns_match:
                column_names = [name.strip() for name in re.sub(r"[|'''\{\}]", "", columns_match.group(1)).split("\n") if name.strip()]
            lyrics_dict = {col: [] for col in column_names}

            # Replace <br /> with newline to treat it as a line break
            tab_content = re.sub(r'<br />', '\n', tab_content)

            # Handle the {{shared|3}} by distributing the lyrics across columns
            for row in tab_content.split('|-'):
                lyrics_parts = [part.strip() for part in row.split("\n") if part.strip()]
                
                # Check if this row is a shared one (contains {{shared|3}})
                if '{{shared|3}}' in row:
                    # Take the row and add it to all columns (this row will have the same content for each column)
                    shared_lyrics = [part for part in row.split("\n") if part.strip() and part != '{{shared|3}}']
                    for idx, col in enumerate(column_names):
                        lyrics_dict[col].append("\n".join(shared_lyrics))  # Add the shared lyrics to all columns
                else:
                    # Normal lyrics row: add to respective columns if there's a match
                    if len(lyrics_parts) == len(column_names):
                        for idx, part in enumerate(lyrics_parts):
                            lyrics_dict[column_names[idx]].append(part.replace('|', ''))

            lyrics[tab_name] = {col: "\n".join(lyrics_dict[col]) for col in lyrics_dict}

        return lyrics

    def extract_date(self, content):
        match = re.search(r"\|(original upload date|date)\s*=\s*\{\{Date\|(.*?)\}\}", content)
        return match.group(2).strip() if match else False

    def extract_singers(self, content): 
        match = re.search(r'\|singer\s*=\s*(.*?)\n', content)
        
        if match:
            singer_line = match.group(1)
            artist_pattern = r'\[\[([^\[\]]+?)\]\]|\{\{Singer\|([^\}]+?)\}\}'
            matches = re.findall(artist_pattern, singer_line)
            singers = []

            for match in matches:
                singer = match[0] if match[0] else match[1]
                singer_list = [s.strip().split('|')[0] for s in singer.split(' and ')]
                singer_list = [(s, f"{self.wiki_url}/wiki/{s.replace(' ', '_')}") for s in singer_list]
                singers.extend(singer_list)

            return singers if singers else False
        return False

    def extract_producers(self, content):
        match = re.search(r'\|producer\s*=\s*(.*?)\n', content)
        if match:
            producer_line = match.group(1)
            matches = re.findall(r"\[\[([^\[\]]+)\]\]\s*\(([^)]+)\)", producer_line)
            producers = [(producer[0], producer[1], f"{self.wiki_url}/wiki/{producer[0].replace(' ', '_')}") for producer in matches]

            return producers if producers else False
        return False

    def extract_views(self, content):
        match = re.search(r"\#views\s*=\s*(.*?)(\n|$)", content)
        return match.group(1) if match else False

    def extract_links(self, content):
        line_with_links = re.search(r'\|link = (.*)', content).group(1)
        pattern = r'\[([^\s]+) ([^\]]+)\](?: <small>(.*?)</small>)?'
        links = [
            (f"{name} {small_text}" if small_text else name, url)
            for url, name, small_text in re.findall(pattern, line_with_links)
        ]
        return links if links else False

    def extract_extra_links(self, content):
        match = re.search(r'(?<=\n==External Links==\n)(.*?)(?=\n==)', content, re.DOTALL)
        if match:
            section_content = match.group(1)
            links = [(name, url) for url, name in re.findall(r'\[(https?://[^\s]+)\s+([^\]]+)\]', section_content)]
            return links if links else False
        return False

    def extract_content_warning(self, content):
        match = re.search(r"\{\{(Questionable|Explicit)\|(.*?)\}\}", content)
        return (match.group(1), match.group(2)) if match else False


page_title = "BUTCHER_VANITY"
page_query = "Miss Death's Idol"

song_info = SongInfo()
song_info.get_page(page_query)

print("Title:", song_info.page_title)
#print("Description:", song_info.page_description)
print("Singers:", song_info.page_singers)
print("Producers:", song_info.page_producers)
print("Image:", song_info.page_image)
print("Date:", song_info.page_date)
print("Views:", song_info.page_views)
print("Links:", song_info.page_links)
print("Extra Links:", song_info.page_extra_links)
print("Content Warning:", song_info.page_content_warning)
print("Lyrics:", song_info.page_lyrics)

