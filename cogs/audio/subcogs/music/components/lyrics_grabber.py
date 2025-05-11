import requests
import mwparserfromhell



class SongInfo:
    def __init__(self):
        self.wiki_url = "https://vocaloidlyrics.fandom.com"
        self.headers = {"User-Agent": "Rei-Chan/1.0"}
        self.query_results = None
        self.page_title = None
        self.wiki_code = None
        self.template = None

    def request_query(self, query):
        url = f"{self.wiki_url}/api.php?action=query&list=search&srsearch={query}&format=json"
        res = requests.get(url, headers=self.headers)
        if res.status_code == 200:
            try:
                results = res.json()['query']['search']
                self.query_results = [(r['title'], f"{self.wiki_url}/wiki/{r['title'].replace(' ', '_')}") for r in results]
                return True
            except KeyError:
                return None
        return False

    def request_page(self, title):
        self.page_title = title
        url = f"{self.wiki_url}/api.php?action=query&prop=revisions&rvprop=content&titles={title}&format=json"
        res = requests.get(url, headers=self.headers)
        if res.status_code == 200:
            pages = res.json()['query']['pages']
            for _, page in pages.items():
                self.wiki_code = mwparserfromhell.parse(page['revisions'][0]['*'])
                print(self.wiki_code)
                return True
        return False
    
    def get_content_warning(self):
        for template in self.wiki_code.filter_templates():
            name = template.name.lower().strip()
            if name in {'explicit', 'questionable'}:
                return (name.capitalize(), template.get(1).value.strip_code().strip())
        return None
    
    def set_template(self, do_alternate: bool = False):
        for template in self.wiki_code.filter_templates():
            name = template.name.strip().lower()
 
            if do_alternate:
                if "alternateversion" in name:
                    self.template = template
                    return True
            else:
                if "infobox_song" in name:
                    self.template = template
                    return True
        return False

    def _template_field(*fields):
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                value = None
                if self.template:
                    for field in fields:
                        if self.template.has(field):
                            value = self.template.get(field).value
                            break
                return func(self, value, *args, **kwargs)
            return wrapper
        return decorator
    
    @_template_field('image')
    def get_image(self, value):
        if not value: return None
        filename = value.strip_code().strip()
        return f"{self.wiki_url}/wiki/File:{filename.replace(' ', '_')}"
    
    @_template_field('songtitle', 'title')
    def get_title(self, value):
        if not value: return None
        value = str(value).replace("<br />", "\n").replace("<br>", "\n")
        parts = [p.strip() for p in value.split("\n") if p.strip()]
        
        titles = []
        for i, part in enumerate(parts):
            text = mwparserfromhell.parse(part).strip_code().strip()
            if ":" in text:
                label, value = text.split(":", 1)
                titles.append((label.strip(), value.strip()))
            else:
                label = "Original" if i == 0 else None
                titles.append((label, text.strip('\'"')))
        return titles
    
    @_template_field('color')
    def get_color(self, value):
        if not value: return None
        color_value = value.strip_code().strip()
        if ";" in color_value: 
            return color_value.split(";")[0].strip()
        return color_value

    @_template_field('original upload date', 'upload_date')
    def get_upload_date(self, value):
        if not value: return None
        date_template = value
        if date_template.strip_code().strip() == "":
            if date_template.filter_templates():
                inner = date_template.filter_templates()[0]
                year = inner.get(1).value.strip_code().strip() if inner.has(1) else ''
                month = inner.get(2).value.strip_code().strip() if inner.has(2) else ''
                day = inner.get(3).value.strip_code().strip() if inner.has(3) else ''
                return f"{month} {day}, {year}"
        else:
            return date_template.strip_code().strip()

    @_template_field('singer')
    def get_singers(self, value):
        if not value: return None
        singers = []
        for node in value.ifilter(recursive=True):
            if isinstance(node, mwparserfromhell.nodes.wikilink.Wikilink):
                title = node.title.strip_code().strip()
                display = node.text.strip_code().strip() if node.text else title
                singers.append((display, f"{self.wiki_url}/wiki/{title.replace(' ', '_')}"))

            elif isinstance(node, mwparserfromhell.nodes.template.Template):
                if node.name.strip().lower() == "singer" and node.has(1):
                    name = node.get(1).value.strip_code().strip()
                    title = name.replace(' ', '_')
                    link = f"{self.wiki_url}/wiki/{title}"
                    singers.append((name, link))

        return singers if singers else None

    @_template_field('producer')
    def get_producers(self, value):
        if not value: return None
        producers = []
        for node in value.ifilter():
            if isinstance(node, mwparserfromhell.nodes.wikilink.Wikilink):
                title = node.title.strip_code().strip()
                display = node.text.strip_code().strip() if node.text else title
                producers.append({"name": display, "link": f"{self.wiki_url}/wiki/{title.replace(' ', '_')}", "note": None})
            elif isinstance(node, mwparserfromhell.nodes.text.Text):
                text = node.strip()
                if text.startswith("(") and text.endswith(")") and producers:
                    producers[-1]["note"] = text.strip("()").strip()

        return [(p["name"], p["note"], p["link"]) for p in producers] if producers else None

    @_template_field('#views')
    def get_views(self, value):
        if value: return value.strip_code().strip()

    @_template_field('link')
    def get_links(self, value):
        if not value: return None
        links = []
        for node in value.ifilter():
            if isinstance(node, mwparserfromhell.nodes.external_link.ExternalLink):
                url = node.url.strip_code().strip()
                text = node.title.strip_code().strip() if node.title else url
                links.append((text, url))
        return links if links else None

    @_template_field('description')
    def get_description(self, value):
        if value: return value.strip_code().strip()
            
    def get_lyrics(self):
        pass
            
    def get_external_links(self):
        sections = self.wiki_code.get_sections(matches='External Links', include_lead=False, include_headings=False)
        if not sections:
            return None

        links = []
        for node in sections[0].ifilter():
            if isinstance(node, mwparserfromhell.nodes.external_link.ExternalLink):
                url = node.url.strip_code().strip()
                text = node.title.strip_code().strip() if node.title else url
                links.append((text, url))
        return links if links else None
    
    def get_unofficial_links(self):
        for section in self.wiki_code.get_sections(include_lead=False, include_headings=True, flat=True):
            heading_node = section.filter_headings(matches=lambda h: h.title.strip_code().strip().lower() == "unofficial")
            if heading_node:
                unofficial_links = []
                for template in section.filter_templates():
                    if template.name.strip().lower() == "vdb" and template.params:
                        code = template.get(1).value.strip_code().strip()
                        unofficial_links.append((f"VDB|{code}", f"https://vocadb.net/{code}"))
                return unofficial_links if unofficial_links else None
        return None
    
    def get_categories(self):
        categories = []
        for node in self.wiki_code.filter_wikilinks():
            title = node.title.strip_code().strip()
            if title.lower().startswith("category:"):
                category_name = title.split(":", 1)[1].strip()
                categories.append((category_name, f"{self.wiki_url}/wiki/{title.replace(' ', '_')}"))
        return categories if categories else None


page_title = "BUTCHER_VANITY"
page_query = "Miss Death's Idol"
#page_query = "のろい_(Noroi)"

song_info = SongInfo()
song_info.request_page(page_query)


print("\ntemplate:")
print(song_info.set_template(do_alternate=False))
print(song_info.template)

print(f"\nResults for '{page_query}':")
print("\ncontent_warning:")
print(song_info.get_content_warning())
print("\nimage:")
print(song_info.get_image())
print("\ntitle:")
print(song_info.get_title())
print("\ncolor:")
print(song_info.get_color())
print("\nupload_date:")
print(song_info.get_upload_date())
print("\nsingers:")
print(song_info.get_singers())
print("\nproducers:")
print(song_info.get_producers())
print("\nviews:")
print(song_info.get_views())
print("\nlinks:")
print(song_info.get_links())
print("\ndescription:")
print(song_info.get_description())
print("\nexternal_links:")
print(song_info.get_external_links())
print("\nunofficial_links:")
print(song_info.get_unofficial_links())
print("\ncategories:")
print(song_info.get_categories())
print("\nlyrics:")
print(song_info.get_lyrics())