# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Course Builder web application entry point."""

__author__ = 'Pavel Simakov (psimakov@google.com)'


import os
import webapp2

# The following import is needed in order to add third-party libraries.
import appengine_config  # pylint: disable-msg=unused-import

from common import tags
from controllers import sites
from models import custom_modules
import modules.admin.admin
import modules.announcements.announcements
import modules.assessment_tags.questions
import modules.course_explorer.course_explorer
import modules.courses.courses
import modules.dashboard.dashboard
import modules.oauth2.oauth2
import modules.oeditor.oeditor
import modules.review.review
import modules.khanex.khanex

import profiles
import profiles.handlers

import gae_mini_profiler.templatetags
import gae_mini_profiler.profiler

import badges
import badges.handlers

# use this flag to control debug only features
debug = not appengine_config.PRODUCTION_MODE

# init and enable most known modules
modules.oeditor.oeditor.register_module().enable()
modules.admin.admin.register_module().enable()
modules.dashboard.dashboard.register_module().enable()
modules.announcements.announcements.register_module().enable()
modules.review.review.register_module().enable()
modules.courses.courses.register_module().enable()
modules.course_explorer.course_explorer.register_module().enable()
modules.assessment_tags.questions.register_module().enable()
modules.khanex.khanex.register_module().enable()

# register modules that are not enabled by default.
modules.oauth2.oauth2.register_module()

# compute all possible routes
global_routes, namespaced_routes = custom_modules.Registry.get_all_routes()


import khan.user_models
from models.models import Student
#create user if logged in and doesn't exist
student = Student.current(True)
if student and hasattr(student, "is_enrolled") and student.is_enrolled == False:
    student.is_enrolled = True
    student.put()




# routes available at '/%namespace%/' context paths
sites.ApplicationRequestHandler.bind(namespaced_routes)
app_routes = [(r'(.*)', sites.ApplicationRequestHandler)]

khan_routes = [('/profile/graph/activity', profiles.handlers.ActivityGraph),
    ('/profile/graph/focus', profiles.handlers.FocusGraph),
    ('/profile/graph/exercisesovertime',
     profiles.handlers.ExercisesOverTimeGraph),
    ('/profile/graph/exerciseproblems',
     profiles.handlers.ExerciseProblemsGraph),

    ('/profile/graph/classexercisesovertime',
     profiles.handlers.ClassExercisesOverTimeGraph),
    ('/profile/graph/classenergypointsperminute',
     profiles.handlers.ClassEnergyPointsPerMinuteGraph),
    ('/profile/graph/classtime', profiles.handlers.ClassTimeGraph),
    ('/profile/(.+?)/(.*)', profiles.handlers.ViewProfile),
    ('/profile/(.*)', profiles.handlers.ViewProfile),
    ('/profile', profiles.handlers.ViewProfile),
    ('/class_profile', profiles.handlers.ViewClassProfile),
    ('/class_profile/(.*)', profiles.handlers.ViewClassProfile),
    ('/badges/(.*)', badges.handlers.ViewBadge),
    ('/badges', badges.handlers.ViewBadge)]
# tag extension resource routes
extensions_tag_resource_routes = [(
    '/extensions/tags/.*/resources/.*', tags.ResourcesHandler)]

# i18n configuration for jinja2
webapp2_i18n_config = {'translations_path': os.path.join(
    appengine_config.BUNDLE_ROOT, 'modules/i18n/resources/locale')}


#from google.appengine.api import namespace_manager
#namespace_manager.set_namespace('ns_editable')
#
#webapp2_extras.jinja2.default_config = {
#    "globals": {
#        "profiler_includes": gae_mini_profiler.templatetags.profiler_includes
#    }
#}

# init application
app = webapp2.WSGIApplication(
    global_routes + extensions_tag_resource_routes + khan_routes + app_routes,
    config={'webapp2_extras.i18n': webapp2_i18n_config},
    debug=debug)

app = gae_mini_profiler.profiler.ProfilerWSGIMiddleware(app)
