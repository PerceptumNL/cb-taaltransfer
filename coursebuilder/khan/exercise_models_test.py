from __future__ import with_statement

import mock
import datetime

from google.appengine.ext import db

#import custom_exceptions
#import coaches
from exercise_models import Exercise
#import phantom_users.phantom_util
from testutil import gae_model
from testutil import mock_datetime
#from coach_resources.coach_request_model import CoachRequest
#from user_models import Capabilities, UserData, UniqueUsername, ParentChildPair
#from user_models import _USER_KEY_PREFIX
from testutil import testsize
from testutil.make_test_db import Exercises, Users, ExercisesAndVideos
#import setting_model
from  exercises import exercise_util
import parser

import logging

from models.models import Student

class ExerciseRequestVideoTest(gae_model.GAEModelTestCase):

    def setUp(self):
        super(ExerciseRequestVideoTest, self).setUp(db_consistency_probability=1)
        self.users = Users()
        self.exercises = Exercises()
        #exercises_and_videos = ExercisesAndVideos(exercises, None)
    def test_request_video(self):
        exs = parser.parse()
        logging.error(exs)
        for ex_name in exs:
            ex = Exercise.get_by_name(ex_name)
            print ex
            if ex == None:
                ex = Exercise(name=ex_name)
                ex.put()
            print ex
                
        #exs = exercise_models.Exercise.all().fetch(1000)
        #user = UserData.current()
        #self.assertFalse(exs[0].video_requested)
        #exs[0].request_video()
        #self.assertTrue(exs[0].video_requested)
        #self.assertEqual(exs[0].video_requests_count, 1)
        #test v1.py

    def test_exercise(self):
        logging.error("EX?")
        logging.error(self.exercises.exponents)
        user_exercise1 = self.users.user1.get_or_insert_exercise(
            self.exercises.exponents)
        for i in range(1,10):
            exercise_util.attempt_problem(self.users.user1, user_exercise1,
                                          i,   # problem_number
                                          1,   # attempt_number
                                          "one",  # attempt_content -- wrong!!
                                          "sha1_unused?",         # sha1
                                          "random_seed",     # random seed
                                          True,  # gotten to the right answer?
                                          0,      # number of hints tried
                                          15,     # time taken (in seconds?)
                                          False,  # being done in review mode?
                                          False,  # being done in topic/power mode?
                                          "obsolete",   # problem_type
                                          "127.0.0.1",  # ip address
                                          {},
                                          "TEST",
                                          "TEST",
                                          1,
                                          7,
                                          async_problem_log_put=False,
                                          async_stack_log_put=False)
        # He's asking for a hint!
