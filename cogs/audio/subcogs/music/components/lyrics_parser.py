import requests

import mwparserfromhell as mw
from mwparserfromhell.nodes.template import Parameter, Template
from mwparserfromhell.nodes.wikilink import Wikilink
from mwparserfromhell.nodes.external_link import ExternalLink
from mwparserfromhell.nodes.text import Text
from mwparserfromhell.smart_list import SmartList

from typing import Callable, Any
from functools import singledispatchmethod



def inject_field(*fields: str) -> Callable:
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            if not self.wiki_code: return None
            if not self.template: 
                if not self.set_template():
                    return None
            for field in fields:
                if self.template.has(field):
                    self._field = self.template.get(field).value
                    return func(self, *args, **kwargs)
        return wrapper
    return decorator

def inject_section(main_heading: str, subheading: str|None = None) -> Callable:
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            section = self.wiki_code.get_sections(matches=main_heading, include_lead=False)
            if not section: return None
            if subheading:
                section = section[0].get_sections(matches=subheading, include_lead=False, include_headings=False)
                if not section: return None
            self._section = section[0]
            return func(self, *args, **kwargs)
        return wrapper
    return decorator



class ParserBase:
    def __init__(self):
        self.wiki_url = "https://vocaloidlyrics.fandom.com"
        self.headers = {"User-Agent": "Rei-Chan/1.0"}
        self.TYPE_LABELS = {
            Template: "template",
            Wikilink: "wikilink",
            ExternalLink: "external"
        }

        self.query: str|None = None
        self.page: str|None = None
        self.wiki_code: mw.wikicode.Wikicode|None = None
        self.template: mw.wikicode.Template|None = None
    
    def request_query(self) -> list[dict[str,str]]|None:
        url = f"{self.wiki_url}/api.php?action=query&list=search&srsearch={self.query}&format=json"
        res = requests.get(url, headers=self.headers)
        if res.status_code == 200:
            try:
                results = res.json()['query']['search']
                return [{"label": r['title'], "link": f"{self.wiki_url}/wiki/{r['title'].replace(' ', '_')}"} for r in results]
            except KeyError:
                return

    def request_page(self) -> bool:
        url = f"{self.wiki_url}/api.php?action=query&prop=revisions&rvprop=content&titles={self.page}&format=json"
        res = requests.get(url, headers=self.headers)
        if res.status_code == 200:
            pages = res.json()['query']['pages']
            for _, page in pages.items():
                self.wiki_code = mw.parse(page['revisions'][0]['*'])
                return True
        return False
    
    def set_template(self, alternate: bool = False) -> bool|None:
        if not self.wiki_code: return None
        template_name = "infobox_song" if not alternate else "alternateversion"
        for template in self.wiki_code.filter_templates():
            if template_name in self.clean(template.name).lower():
                self.template = template
                return True
        return False
    
    def clean(self, node, targ: str|None = None):
        return node.strip_code().strip(targ)
    
    def parse_title(self, line) -> dict|None:
        text = self.clean(mw.parse(line), '\'" ')
        if not text: return None
        if ':' in text: 
            label, value = map(str.strip, text.split(':', 1))
            return {"language": label, "title": value}
        else: 
            return {"language": None, "title": text}
        
    @singledispatchmethod
    def parse_node(self, node: Any) -> dict|None:
        return None
    
    @parse_node.register(Template)
    def template_link(self, node: Template) -> dict|None:
        if node.name.strip().lower() == "vdb" and node.has(1):
            return {"label": "VocaDB", "link": f"https://vocadb.net/{self.clean(node.get(1).value)}"}
        elif node.has(1):
            title = self.clean(node.get(1).value)
            return {"label": title, "link": f"{self.wiki_url}/wiki/{title.replace(' ', '_')}"}
        
    @parse_node.register(Wikilink)
    def wiki_link(self, node: Wikilink) -> dict|None:
        label = title = self.clean(node.title or node.text)
        if title.lower().startswith("category:"): 
            label = title.split(":", 1)[1].strip()
        return {"label": label, "link": f"{self.wiki_url}/wiki/{title.replace(' ', '_')}"}
    
    @parse_node.register(ExternalLink)
    def external_link(self, node: ExternalLink) -> dict|None:
        return {"label": self.clean(node.title), "link": self.clean(node.url)}
    
    def parse_links(self, source, *, include=("external", "wikilink", "template"), filter_func=None, enrich=None) -> list[dict]|None:
        links = []
        
        for node in source.ifilter(recursive=True):
            if filter_func and not filter_func(node): continue
            if self.TYPE_LABELS.get(type(node)) not in include: continue
            link = self.parse_node(node)
            if enrich: enrich(node, link, links)
            if not link: continue
            links.append(link)

        return links or None
    
    # Enrich function for parse_links
    def link_notes(self, node, link, links) -> None:
        if isinstance(node, Text):
            text = node.strip()
            if text.startswith("(") and text.endswith(")") and links:
                links[-1]["note"] = text.strip("( )")



class VocaloidParser(ParserBase):
    def __init__(self):
        super().__init__()
        self._field: Parameter
        self._section: SmartList

    def get_query_results(self, query: str):
        self.query = query
        return self.request_query()
    
    def set_page(self, page: str|None = None, alternate: bool = False):
        if not self.page and not page: return
        if not self.page and page: self.page = page
        return self.request_page() and self.set_template(alternate)
    
    def get_content_warning(self):
        if not self.wiki_code: return None

        epilepsy_present = False
        for template in self.wiki_code.filter_templates():
            name = template.name.lower().strip()
            if name == "epilepsy": epilepsy_present = True
            if name in {"explicit", "questionable"} and template.has(1):
                return {
                    "type": name.capitalize(),
                    "label": self.clean(template.get(1).value),
                    "epilepsy": epilepsy_present
                }

        return {"type": None, "label": None, "epilepsy": True} if epilepsy_present else None
    
    @inject_field('image')
    def get_image(self):
        return f"{self.wiki_url}/wiki/File:{self.clean(self._field).replace(' ', '_')}"
    
    @inject_field('songtitle', 'title')
    def get_titles(self):
        lines = str(self._field).replace("<br />", "\n").replace("<br>", "\n").split("\n")
        return [title for line in filter(None, lines) if (title := self.parse_title(line))] or None
    
    @inject_field('color')
    def get_color(self):
        colors = tuple(map(str.strip, self._field.split("; color:", 1)))
        return {"main": colors[0], "highlight": colors[1] if len(colors) > 1 else None}

    @inject_field('original upload date', 'date')
    def get_date(self):
        date_template = self._field.filter_templates()
        if not date_template: return self.clean(self._field)
        get = lambda n: self.clean(date_template[0].get(n).value)
        return f"{get(1)} {get(2)}, {get(3)}"

    @inject_field('singer')
    def get_singers(self):
        return self.parse_links(self._field, include=["wikilink", "template"])

    @inject_field('producer')
    def get_producers(self):
        return self.parse_links(self._field, enrich=self.link_notes)

    @inject_field('#views')
    def get_views(self):
        return self.clean(self._field) or None

    @inject_field('link')
    def get_links(self):
        return self.parse_links(self._field, include=["external"])

    @inject_field('description')
    def get_description(self):
        return self.clean(self._field) or None
    
    # TODO: Parse lyrics.
    @inject_section('Lyrics')
    def get_lyrics(self):
        print("[DEBUG] Parsing lyrics headers")

        lines = str(self._section).splitlines()

        headers = None
        for line in lines:
            line = line.strip()
            if line.startswith("|") and "||" in line:
                raw_cells = line.strip("|").split("||")
                headers = [self.clean(mw.parse(cell), "'") for cell in raw_cells]
                break 

        if not headers:
            print("[DEBUG] No header row found.")
            return None

        print(f"[DEBUG] Found headers: {headers}")

        lyrics_data = {header: [] for header in headers}
        print(f"[DEBUG] Initialized lyrics data structure: {lyrics_data}")

        return lyrics_data
            
    @inject_section('External Links')
    def get_external_links(self):
        return self.parse_links(self._section, include=["external"])
    
    @inject_section('External Links', 'Unofficial')
    def get_unofficial_links(self):
        return self.parse_links(self._section, include=["external", "template"])

    @inject_section('External Links', 'Unofficial')
    def get_categories(self):
        filter = lambda node: isinstance(node, Wikilink) and self.clean(node.title).startswith("Category:")
        return self.parse_links(self._section, include=["wikilink"], filter_func=filter)
    
    def extract_page(self):
        return {
            "content_warning": self.get_content_warning(),
            "image": self.get_image(),
            "title": self.get_titles(),
            "color": self.get_color(),
            "date": self.get_date(),
            "singers": self.get_singers(),
            "producers": self.get_producers(),
            "views": self.get_views(),
            "links": self.get_links(),
            "description": self.get_description(),
            "lyrics": self.get_lyrics(),
            "external_links": self.get_external_links(),
            "unofficial_links": self.get_unofficial_links(),
            "categories": self.get_categories()
        }
    


page_query = "BUTCHER_VANITY"
#page_query = "Miss Death's Idol"
#page_query = "のろい_(Noroi)"
#page_query = "カゼマチグサ_(Kazemachigusa)"
#page_query = "Splitter_Girl"

song_info = VocaloidParser()
#print(song_info.get_query_results(page_query))

song_info.set_page(page_query, alternate=False)

song_info.get_lyrics()
'''
stuff = song_info.extract_page()
for x in stuff:
    print(f"\n{x}:\n{stuff[x]}")'''
