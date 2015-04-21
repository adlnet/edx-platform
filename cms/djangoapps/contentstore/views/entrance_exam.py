"""
Entrance Exams view module -- handles all requests related to entrance exam management via Studio
Intended to be utilized as an AJAX callback handler, versus a proper view/screen
"""
from functools import wraps
import json
import logging

from django.contrib.auth.decorators import login_required
from django_future.csrf import ensure_csrf_cookie
from django.http import HttpResponse, HttpResponseBadRequest

from contentstore.views.helpers import create_xblock
from contentstore.views.item import delete_item
from models.settings.course_metadata import CourseMetadata
from opaque_keys.edx.keys import CourseKey, UsageKey
from opaque_keys import InvalidKeyError
from student.auth import has_course_author_access
from util import milestones_helpers
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import ItemNotFoundError
from django.conf import settings
from django.utils.translation import ugettext as _

__all__ = ['entrance_exam', ]

log = logging.getLogger(__name__)


# pylint: disable=invalid-name
def _get_default_entrance_exam_minimum_pct():
    """
    Helper method to return the default value from configuration
    Converts integer values to decimals, since that what we use internally
    """
    entrance_exam_minimum_score_pct = float(settings.ENTRANCE_EXAM_MIN_SCORE_PCT)
    if entrance_exam_minimum_score_pct.is_integer():
        entrance_exam_minimum_score_pct = entrance_exam_minimum_score_pct / 100
    return entrance_exam_minimum_score_pct


# pylint: disable=missing-docstring
def check_feature_enabled(feature_name):
    """
    Ensure the specified feature is turned on.  Return an HTTP 400 code if not.
    """
    def _check_feature_enabled(view_func):
        def _decorator(request, *args, **kwargs):
            # Deny access if the entrance exam feature is disabled
            if not settings.FEATURES.get(feature_name, False):
                return HttpResponseBadRequest()
            return view_func(request, *args, **kwargs)
        return wraps(view_func)(_decorator)
    return _check_feature_enabled


@login_required
@ensure_csrf_cookie
@check_feature_enabled(feature_name='ENTRANCE_EXAMS')
def entrance_exam(request, course_key_string):
    """
    The restful handler for entrance exams.
    It allows retrieval of all the assets (as an HTML page), as well as uploading new assets,
    deleting assets, and changing the "locked" state of an asset.

    GET
        Retrieves the entrance exam module (metadata) for the specified course
    POST
        Adds an entrance exam module to the specified course.
    DELETE
        Removes the entrance exam from the course
    """
    course_key = CourseKey.from_string(course_key_string)

    # Deny access if the user is valid, but they lack the proper object access privileges
    if not has_course_author_access(request.user, course_key):
        return HttpResponse(status=403)

    # Retrieve the entrance exam module for the specified course (returns 404 if none found)
    if request.method == 'GET':
        return _get_entrance_exam(request, course_key)

    # Create a new entrance exam for the specified course (returns 201 if created)
    elif request.method == 'POST':
        response_format = request.REQUEST.get('format', 'html')
        http_accept = request.META.get('http_accept')
        if response_format == 'json' or 'application/json' in http_accept:
            ee_min_score = request.POST.get('entrance_exam_minimum_score_pct', None)

            # if request contains empty value or none then save the default one.
            entrance_exam_minimum_score_pct = _get_default_entrance_exam_minimum_pct()
            if ee_min_score != '' and ee_min_score is not None:
                entrance_exam_minimum_score_pct = float(ee_min_score)
            return create_entrance_exam(request, course_key, entrance_exam_minimum_score_pct)
        return HttpResponse(status=400)

    # Remove the entrance exam module for the specified course (returns 204 regardless of existence)
    elif request.method == 'DELETE':
        return delete_entrance_exam(request, course_key)

    # No other HTTP verbs/methods are supported at this time
    else:
        return HttpResponse(status=405)


@check_feature_enabled(feature_name='ENTRANCE_EXAMS')
def create_entrance_exam(request, course_key, entrance_exam_minimum_score_pct):
    """
    api method to create an entrance exam.
    First clean out any old entrance exams.
    """
    _delete_entrance_exam(request, course_key)
    return _create_entrance_exam(
        request=request,
        course_key=course_key,
        entrance_exam_minimum_score_pct=entrance_exam_minimum_score_pct
    )


def _create_entrance_exam(request, course_key, entrance_exam_minimum_score_pct=None):
    """
    Internal workflow operation to create an entrance exam
    """
    # Provide a default value for the minimum score percent if nothing specified
    if entrance_exam_minimum_score_pct is None:
        entrance_exam_minimum_score_pct = _get_default_entrance_exam_minimum_pct()

    # Confirm the course exists
    course = modulestore().get_course(course_key)
    if course is None:
        return HttpResponse(status=400)

    # Create the entrance exam item (currently it's just a chapter)
    payload = {
        'category': "chapter",
        'display_name': _("Entrance Exam"),
        'parent_locator': unicode(course.location),
        'is_entrance_exam': True,
        'in_entrance_exam': True,
    }
    parent_locator = unicode(course.location)
    created_block = create_xblock(
        parent_locator=parent_locator,
        user=request.user,
        category='chapter',
        display_name=_('Entrance Exam'),
        is_entrance_exam=True
    )

    # Set the entrance exam metadata flags for this course
    # Reload the course so we don't overwrite the new child reference
    course = modulestore().get_course(course_key)
    metadata = {
        'entrance_exam_enabled': True,
        'entrance_exam_minimum_score_pct': unicode(entrance_exam_minimum_score_pct),
        'entrance_exam_id': unicode(created_block.location),
    }
    CourseMetadata.update_from_dict(metadata, course, request.user)

    # Create the entrance exam section item.
    create_xblock(
        parent_locator=unicode(created_block.location),
        user=request.user,
        category='sequential',
        display_name=_('Entrance Exam - Subsection')
    )

    # Add an entrance exam milestone if one does not already exist
    namespace_choices = milestones_helpers.get_namespace_choices()
    milestone_namespace = milestones_helpers.generate_milestone_namespace(
        namespace_choices.get('ENTRANCE_EXAM'),
        course_key
    )
    milestones = milestones_helpers.get_milestones(milestone_namespace)
    if len(milestones):
        milestone = milestones[0]
    else:
        description = 'Autogenerated during {} entrance exam creation.'.format(unicode(course.id))
        milestone = milestones_helpers.add_milestone({
            'name': _('Completed Course Entrance Exam'),
            'namespace': milestone_namespace,
            'description': description
        })
    relationship_types = milestones_helpers.get_milestone_relationship_types()
    milestones_helpers.add_course_milestone(
        unicode(course.id),
        relationship_types['REQUIRES'],
        milestone
    )
    milestones_helpers.add_course_content_milestone(
        unicode(course.id),
        unicode(created_block.location),
        relationship_types['FULFILLS'],
        milestone
    )

    return HttpResponse(status=201)


def _get_entrance_exam(request, course_key):  # pylint: disable=W0613
    """
    Internal workflow operation to retrieve an entrance exam
    """
    course = modulestore().get_course(course_key)
    if course is None:
        return HttpResponse(status=400)
    if not getattr(course, 'entrance_exam_id'):
        return HttpResponse(status=404)
    try:
        exam_key = UsageKey.from_string(course.entrance_exam_id)
    except InvalidKeyError:
        return HttpResponse(status=404)
    try:
        exam_descriptor = modulestore().get_item(exam_key)
        return HttpResponse(
            _serialize_entrance_exam(exam_descriptor),
            status=200, mimetype='application/json')
    except ItemNotFoundError:
        return HttpResponse(status=404)


@check_feature_enabled(feature_name='ENTRANCE_EXAMS')
def update_entrance_exam(request, course_key, exam_data):
    """
    Operation to update course fields pertaining to entrance exams
    The update operation is not currently exposed directly via the API
    Because the operation is not exposed directly, we do not return a 200 response
    But we do return a 400 in the error case because the workflow is executed in a request context
    """
    course = modulestore().get_course(course_key)
    if course:
        metadata = exam_data
        CourseMetadata.update_from_dict(metadata, course, request.user)


@check_feature_enabled(feature_name='ENTRANCE_EXAMS')
def delete_entrance_exam(request, course_key):
    """
    api method to delete an entrance exam
    """
    return _delete_entrance_exam(request=request, course_key=course_key)


def _delete_entrance_exam(request, course_key):
    """
    Internal workflow operation to remove an entrance exam
    """
    store = modulestore()
    course = store.get_course(course_key)
    if course is None:
        return HttpResponse(status=400)

    course_children = store.get_items(
        course_key,
        qualifiers={'category': 'chapter'}
    )
    for course_child in course_children:
        if course_child.is_entrance_exam:
            delete_item(request, course_child.scope_ids.usage_id)
            milestones_helpers.remove_content_references(unicode(course_child.scope_ids.usage_id))

    # Reset the entrance exam flags on the course
    # Reload the course so we have the latest state
    course = store.get_course(course_key)
    if getattr(course, 'entrance_exam_id'):
        metadata = {
            'entrance_exam_enabled': False,
            'entrance_exam_minimum_score_pct': None,
            'entrance_exam_id': None,
        }
        CourseMetadata.update_from_dict(metadata, course, request.user)

    return HttpResponse(status=204)


def _serialize_entrance_exam(entrance_exam_module):
    """
    Internal helper to convert an entrance exam module/object into JSON
    """
    return json.dumps({
        'locator': unicode(entrance_exam_module.location)
    })
