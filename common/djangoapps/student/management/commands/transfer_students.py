from opaque_keys.edx.keys import CourseKey
from optparse import make_option
from django.contrib.auth.models import User
from student.models import CourseEnrollment
from shoppingcart.models import CertificateItem
from track.management.tracked_command import TrackedCommand


class Command(TrackedCommand):
    help = """
    This command takes two course ids as input and transfers
    all students enrolled in one course into the other.  This will
    remove them from the first class and enroll them in the specified
    class(es) in the same mode as the first one. eg. honor, verified,
    audit.

    example:
        # Transfer students from the old demoX class to a new one.
        manage.py ... transfer_students -f edX/Open_DemoX/edx_demo_course -t edX/Open_DemoX/new_demoX

        # Transfer students from the old demoX class into two new classes.
        manage.py ... transfer_students -f edX/Open_DemoX/edx_demo_course -t edX/Open_DemoX/new_demoX,edX/Open_DemoX/edX_Insider
    """

    option_list = TrackedCommand.option_list + (
        make_option('-f', '--from',
                    metavar='SOURCE_COURSE',
                    dest='source_course',
                    help='The course to transfer students from.'),
        make_option('-t', '--to',
                    metavar='DEST_COURSE_LIST',
                    dest='dest_course_list',
                    help='The new course(es) to enroll the student into.'),
    )

    def handle(self, *args, **options):
        source_key = CourseKey.from_string(options['source_course'])
        dest_keys = []
        for course_key in options['dest_course_list'].split(','):
            dest_keys.append(CourseKey.from_string(course_key))

        source_students = User.objects.filter(
            courseenrollment__course_id=source_key
        )

        for user in source_students:
            print("Moving {}.".format(user.username))
            # Find the old enrollment.
            enrollment = CourseEnrollment.objects.get(
                user=user,
                course_id=source_key
            )

            # Move the Student between the classes.
            mode = enrollment.mode
            old_is_active = enrollment.is_active
            CourseEnrollment.unenroll(user, source_key)
            print("Unenrolled {} from {}".format(user.username, unicode(source_key)))

            for dest_key in dest_keys:
                if CourseEnrollment.is_enrolled(user, dest_key):
                    # Un Enroll from source course but don't mess
                    # with the enrollment in the destination course.
                    msg = "Skipping {}, already enrolled in destination course {}"
                    print(msg.format(user.username, unicode(dest_key)))
                    continue

                new_enrollment = CourseEnrollment.enroll(user, dest_key, mode=mode)

                # Unenroll from the new coures if the user had unenrolled
                # form the old course.
                if not old_is_active:
                    new_enrollment.update_enrollment(is_active=False)

                if mode == 'verified':
                    try:
                        certificate_item = CertificateItem.objects.get(
                            course_id=source_key,
                            course_enrollment=enrollment
                        )
                    except CertificateItem.DoesNotExist:
                        print("No certificate for {}".format(user))
                        continue

                    certificate_item.course_id = dest_key
                    certificate_item.course_enrollment = new_enrollment
                    certificate_item.save()
