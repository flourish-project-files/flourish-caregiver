from dateutil.relativedelta import relativedelta
from django.test import TestCase, tag
from edc_appointment.models import Appointment
from edc_base.utils import get_utcnow
from edc_constants.constants import POS
from edc_constants.constants import YES, NO
from edc_facility.import_holidays import import_holidays
from edc_metadata import REQUIRED, NOT_REQUIRED
from edc_metadata.models import CrfMetadata
from edc_visit_tracking.constants import SCHEDULED
from model_mommy import mommy

from flourish_child.models import ChildDummySubjectConsent
from ..helper_classes import MaternalStatusHelper
from ..models.onschedule import OnScheduleCohortATb2Months, OnScheduleCohortAAntenatal, \
    OnScheduleCohortAQuarterly
from ..models import CaregiverOffSchedule


@tag('tb')
class TestVisitScheduleTb(TestCase):

    def setUp(self):
        import_holidays()
        self.subject_identifier = '12345678'
        self.study_maternal_identifier = '89721'

        self.user = mommy.make('User',
                               username='Megan',
                               is_active=True)
        self.user.set_password('password')
        self.user.save()

        self.options = {
            'consent_datetime': get_utcnow(),
            'version': '1'
        }

        self.subject_screening = mommy.make_recipe(
            'flourish_caregiver.screeningpregwomen')

        self.eligible_options = {
            'screening_identifier': self.subject_screening.screening_identifier,
            'consent_datetime': get_utcnow,
            'remain_in_study': YES,
            'hiv_testing': YES,
            'breastfeed_intent': YES,
            'consent_reviewed': YES,
            'study_questions': YES,
            'assessment_score': YES,
            'consent_signature': YES,
            'consent_copy': YES
        }
        self.consent = mommy.make_recipe('flourish_caregiver.subjectconsent',
                                         **self.eligible_options)

        self.child_consent = mommy.make_recipe(
            'flourish_caregiver.caregiverchildconsent',
            subject_consent=self.consent,
            gender=None,
            first_name=None,
            last_name=None,
            identity=None,
            confirm_identity=None,
            study_child_identifier=None,
            child_dob=None,
            preg_enroll=True,
            version='2')

        mommy.make_recipe(
            'flourish_caregiver.antenatalenrollment',
            subject_identifier=self.consent.subject_identifier)

        self.status_helper = MaternalStatusHelper(
            subject_identifier=self.consent.subject_identifier)

        self.enrol_visit = mommy.make_recipe(
            'flourish_caregiver.maternalvisit',
            appointment=Appointment.objects.get(
                visit_code='1000M',
                subject_identifier=self.consent.subject_identifier),
            report_datetime=get_utcnow(),
            reason=SCHEDULED)

    def test_put_on_tb_schedule(self):
        """
        Test if a subject is put the tb schedule successfully
        """
        mommy.make_recipe(
            'flourish_caregiver.tbinformedconsent',
            subject_identifier=self.consent.subject_identifier,
            consent_datetime=get_utcnow()
        )
        self.assertEqual(OnScheduleCohortATb2Months.objects.filter(
            subject_identifier=self.consent.subject_identifier,
            schedule_name='tb_2_months_schedule').count(), 0)

        mommy.make_recipe(
            'flourish_caregiver.maternaldelivery',
            subject_identifier=self.consent.subject_identifier, )

        self.assertEqual(OnScheduleCohortATb2Months.objects.filter(
            subject_identifier=self.consent.subject_identifier,
            schedule_name='tb_2_months_schedule').count(), 1)

    @tag('tb_off')
    def test_tb_referral_required(self):
        """
        Test if the off study crf succesfully removes an individul from the Tb schedule
        """

        mommy.make_recipe(
            'flourish_caregiver.tbinformedconsent',
            subject_identifier=self.consent.subject_identifier,
            consent_datetime=get_utcnow()
        )
        self.assertEqual(OnScheduleCohortATb2Months.objects.filter(
            subject_identifier=self.consent.subject_identifier,
            schedule_name='tb_2_months_schedule').count(), 0)

        mommy.make_recipe(
            'flourish_caregiver.maternaldelivery',
            subject_identifier=self.consent.subject_identifier, )

        child_consent = ChildDummySubjectConsent.objects.get(
            subject_identifier=self.child_consent.subject_identifier,
        )

        child_consent.dob = (get_utcnow() - relativedelta(days=1)).date()
        child_consent.save()

        mommy.make_recipe(
            'flourish_caregiver.maternalvisit',
            appointment=Appointment.objects.get(
                subject_identifier=self.consent.subject_identifier,
                visit_code='2000D'),
            report_datetime=get_utcnow(),
            reason=SCHEDULED)

        self.assertEqual(OnScheduleCohortATb2Months.objects.filter(
            subject_identifier=self.consent.subject_identifier,
            schedule_name='tb_2_months_schedule').count(), 1)

        tb_visit = mommy.make_recipe(
            'flourish_caregiver.maternalvisit',
            appointment=Appointment.objects.get(
                subject_identifier=self.consent.subject_identifier,
                visit_code='2100T'),
            report_datetime=get_utcnow(),
            reason=SCHEDULED)

        self.assertEqual(CrfMetadata.objects.get(
            model='flourish_caregiver.tbreferral',
            subject_identifier=self.consent.subject_identifier,
            visit_code='2100T').entry_status, NOT_REQUIRED)

        mommy.make_recipe('flourish_caregiver.tbvisitscreeningwomen',
                          have_cough=YES,
                          maternal_visit=tb_visit)

        self.assertEqual(CrfMetadata.objects.get(
            model='flourish_caregiver.tbreferral',
            subject_identifier=self.consent.subject_identifier,
            visit_code='2100T').entry_status, REQUIRED)

    def test_tb_screening_form(self):

        self.assertEqual(CrfMetadata.objects.get(
            model='flourish_caregiver.tbstudyeligibility',
            subject_identifier=self.consent.subject_identifier,
            visit_code='1000M').entry_status, NOT_REQUIRED)

        mommy.make_recipe('flourish_caregiver.ultrasound',
                          maternal_visit=self.enrol_visit,
                          ga_confirmed=22)

        self.assertEqual(CrfMetadata.objects.get(
            model='flourish_caregiver.tbstudyeligibility',
            subject_identifier=self.consent.subject_identifier,
            visit_code='1000M').entry_status, REQUIRED)
