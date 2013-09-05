import inspect
import logging
import mimetypes
import os
import pkgutil
from xml.etree import cElementTree
import html5lib
import exercise_models

#import safe_dom
from common import safe_dom

_str = '<p>In deze lessen ga je leren over getallen tot en met 100. We beginnen met de getallen tot en met 100 aan je voorstellen.\
Maak nu de volgende opdracht. </p>\
<p>In deze opdracht maak je kennis met de uitspraak en uitgeschreven schrijfwijze van verschillende getallen</p>\
<br><span><khanex name="getallen_tot_100_lezen"></khanex></span><span><br></span>\
<p>Is het gelukt? Nu je over dit onderwerp heb geleerd, mag je naar het volgend onderdeel gaan.</p>'


def html_string_to_element_tree(html_string):
    parser = html5lib.HTMLParser(
        tree=html5lib.treebuilders.getTreeBuilder('etree', cElementTree),
        namespaceHTMLElements=False)
    return parser.parseFragment('<div>%s</div>' % html_string)[0]


def html_to_safe_dom(html_string, handler):
    """Render HTML text as a tree of safe_dom elements."""

    node_list = []
    if not html_string:
        return node_list

    def _process_html_tree(elt):
        tail = elt.tail
        try:
            for child in elt:
                if child.tag == "khanex":
                    node_list.append(child)

        except Exception as e:  # pylint: disable-msg=broad-except
            logging.error('Invalid HTML tag: %s. %s', elt, e)
        return node_list

    root = html_string_to_element_tree(html_string)

    for elt in root:
        _process_html_tree(elt)

    return node_list


class LessonExercises():

    def parse(self, html_str=None):
    
        if html_str == None: html_str = _str
    
        exs = html_to_safe_dom(html_str, None)
        exs_names = []
        for ex in exs:
            print ex.tag
            print ex.get('name')
            exs_names.append(ex.get('name'))
                
        return exs_names

    def update(self, html_str):
        from google.appengine.api import namespace_manager
    
        namespace = namespace_manager.get_namespace()
        logging.error(namespace)
        exs =  self.parse(html_str)
        _all = exercise_models.Exercise.all().fetch(100)
        logging.error(_all)
        for ex_name in exs:
            logging.error("f")
            logging.error(ex_name)
            
            ex = exercise_models.Exercise.all().filter("name =", ex_name).get()
#get_by_name(ex_name)
            if ex == None:
                logging.error("New exercise: %s" % ex_name)
                ex = exercise_models.Exercise(name=ex_name)
                ex.put()
            else:
                logging.error("Found exercise: %s" % ex_name)
