import requests
import mwparserfromhell as mw
from typing import Callable
from functools import singledispatchmethod



def inject_field(*fields: str) -> Callable:
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            if not self.template: self.set_template()
            for field in fields:
                if self.template.has(field):
                    return func(self, self.template.get(field).value, *args, **kwargs)
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
            return func(self, section[0], *args, **kwargs)
        return wrapper
    return decorator



class ParserBase:
    def __init__(self):
        self.wiki_url = "https://vocaloidlyrics.fandom.com"
        self.headers = {"User-Agent": "Rei-Chan/1.0"}
        self.query = None
        self.page = None
        self.wiki_code = None
        self.template = None
        self.TYPE_LABELS = {
            mw.nodes.template.Template: "template",
            mw.nodes.wikilink.Wikilink: "wikilink",
            mw.nodes.external_link.ExternalLink: "external"
        }
    
    def request_query(self) -> list[any]|None:
        url = f"{self.wiki_url}/api.php?action=query&list=search&srsearch={self.query}&format=json"
        res = requests.get(url, headers=self.headers)
        if res.status_code == 200:
            try:
                results = res.json()['query']['search']
                return [(r['title'], f"{self.wiki_url}/wiki/{r['title'].replace(' ', '_')}") for r in results]
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
    
    def clean(self, node, targ: str = None):
        return node.strip_code().strip(targ)
    
    def parse_title(self, line) -> dict:
        text = self.clean(mw.parse(line), '\'" ')
        if not text: return None
        if ':' in text: 
            label, value = map(str.strip, text.split(':', 1))
            return {"language": label, "title": value}
        else: 
            return {"language": None, "title": text}
        
    @singledispatchmethod
    def parse_node(self, node):
        return None
    
    @parse_node.register(mw.nodes.template.Template)
    def template_link(self, node) -> dict|None:
        if node.name.strip().lower() == "vdb" and node.has(1):
            return {"label": "VocaDB", "link": f"https://vocadb.net/{self.clean(node.get(1).value)}"}
        elif node.has(1):
            title = self.clean(node.get(1).value)
            return {"label": title, "link": f"{self.wiki_url}/wiki/{title.replace(' ', '_')}"}
        
    @parse_node.register(mw.nodes.wikilink.Wikilink)
    def wiki_link(self, node) -> dict|None:
        label = title = self.clean(node.title or node.text)
        if title.lower().startswith("category:"): 
            label = title.split(":", 1)[1].strip()
        return {"label": label, "link": f"{self.wiki_url}/wiki/{title.replace(' ', '_')}"}
    
    @parse_node.register(mw.nodes.external_link.ExternalLink)
    def external_link(self, node) -> dict|None:
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
        if isinstance(node, mw.nodes.text.Text):
            text = node.strip()
            if text.startswith("(") and text.endswith(")") and links:
                links[-1]["note"] = text.strip("( )")



class VocaloidParser(ParserBase):
    def __init__(self):
        super().__init__()

    def get_query_results(self, query):
        self.query = query
        return self.request_query()
    
    def set_page(self, page):
        self.page = page
        return self.request_page()
    
    def set_template(self, do_alternate: bool = False) -> bool:
        template_name = "infobox_song" if not do_alternate else "alternateversion"
        for template in self.wiki_code.filter_templates():
            if template_name in self.clean(template.name).lower():
                self.template = template
                return True
        return False
    
    # TODO: Add a boolean for epilepsy.
    def get_content_warning(self):
        return next((
            {"type": name.capitalize() ,
            "label": self.clean(template.get(1).value)}
            for template in self.wiki_code.filter_templates()
            if (name := template.name.lower().strip()) in {"explicit", "questionable"}
        ), None)
    
    @inject_field('image')
    def get_image(self, field):
        return f"{self.wiki_url}/wiki/File:{self.clean(field).replace(' ', '_')}"
    
    @inject_field('songtitle', 'title')
    def get_titles(self, field):
        lines = str(field).replace("<br />", "\n").replace("<br>", "\n").split("\n")
        return [title for line in filter(None, lines) if (title := self.parse_title(line))] or None
    
    @inject_field('color')
    def get_color(self, field):
        colors = tuple(map(str.strip, field.split("; color:", 1)))
        return {"main": colors[0], "highlight": colors[1] if len(colors) > 1 else None}

    @inject_field('original upload date', 'date')
    def get_date(self, field):
        date_template = field.filter_templates()
        if not date_template: return self.clean(field)
        get = lambda n: self.clean(date_template[0].get(n).value)
        return f"{get(1)} {get(2)}, {get(3)}"

    @inject_field('singer')
    def get_singers(self, field):
        return self.parse_links(field, include=["wikilink", "template"])

    @inject_field('producer')
    def get_producers(self, field):
        return self.parse_links(field, enrich=self.link_notes)

    @inject_field('#views')
    def get_views(self, field):
        return self.clean(field) or None

    @inject_field('link')
    def get_links(self, field):
        return self.parse_links(field, include=["external"])

    @inject_field('description')
    def get_description(self, field):
        return self.clean(field) or None
    
    # TODO: Parse lyrics.
    def get_lyrics(self):
        return
            
    @inject_section('External Links')
    def get_external_links(self, section):
        return self.parse_links(section, include=["external"])
    
    @inject_section('External Links', 'Unofficial')
    def get_unofficial_links(self, section):
        return self.parse_links(section, include=["external", "template"])

    @inject_section('External Links', 'Unofficial')
    def get_categories(self, section):
        filter = lambda node: isinstance(node, mw.nodes.wikilink.Wikilink) and self.clean(node.title).startswith("Category:")
        return self.parse_links(section, include=["wikilink"], filter_func=filter)
    
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
page_query = "Miss Death's Idol"
page_query = "のろい_(Noroi)"
page_query = "カゼマチグサ_(Kazemachigusa)"

song_info = VocaloidParser()
print(song_info.get_query_results(page_query))
song_info.set_page(page_query)

print("\ntemplate:")
print(song_info.set_template(do_alternate=False))
print(song_info.template)

stuff = song_info.extract_page()
for x in stuff:
    print(f"\n{x}:\n{stuff[x]}")
