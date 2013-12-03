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

def get_khanex_dict(html_string):
    root = html_string_to_element_tree(html_string)
    khanex_list = root.findall('khanex')

    khanex_dict = {}

    for khanex in khanex_list:
        khanex_dict[khanex.attrib['name']] = {}

    return khanex_dict

def UpdateExercises(lesson):
    from google.appengine.api import namespace_manager
    namespace = namespace_manager.get_namespace()

    ex_name_list = get_khanex_dict(lesson.objectives).keys()

    ex_list = []
    for ex_name in ex_name_list:
        ex = exercise_models.Exercise.all().filter("name =", ex_name).get()
        if ex == None:
            ex = exercise_models.Exercise(name=ex_name)
            ex.lesson_id = lesson.lesson_id
            ex.unit_id = lesson.unit_id
            ex.pretty_display_name = lesson.title
            ex.put()
            logging.error("New exercise: %s" % ex_name)
        else:
            ex.lesson_id = lesson.lesson_id
            ex.unit_id = lesson.unit_id
            ex.pretty_display_name = lesson.title
            ex.put()
            logging.error("Update exercise: %s" % ex_name)
        ex_list.append(ex)
    return ex_list
    
