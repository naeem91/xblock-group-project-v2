from unittest import TestCase
import ddt
import mock
from xblock.field_data import DictFieldData
from group_project_v2.group_project import GroupActivityXBlock
from group_project_v2.project_api import ProjectAPI
from group_project_v2.stage import EvaluationDisplayStage, GradeDisplayStage
from tests.utils import TestWithPatchesMixin, make_review_item


class BaseStageTest(TestCase, TestWithPatchesMixin):
    block_to_test = None
    user_id = 1
    workgroup_data = {
        "id": 1,
        "users": [
            {"id": 1}, {"id": 2}, {"id": 3}
        ]
    }

    def setUp(self):
        self.runtime_mock = mock.Mock()
        self.activity_mock = mock.create_autospec(GroupActivityXBlock)
        self.activity_mock.content_id = '123456'
        # can't use create_autospec here, as most methods are wrapped in decorators and mock fails signature checks
        # with "Too many positional arguments" because of this
        self.project_api_mock = mock.Mock(spec_set=ProjectAPI)

        # pylint: disable=not-callable
        self.block = self.block_to_test(self.runtime_mock, field_data=DictFieldData({}), scope_ids=mock.Mock())
        self.make_patch(self.block_to_test, 'project_api', mock.PropertyMock(return_value=self.project_api_mock))
        self.make_patch(self.block_to_test, 'activity', mock.PropertyMock(return_value=self.activity_mock))
        self.real_user_id_mock = self.make_patch(self.block, 'real_user_id', mock.Mock(side_effect=lambda u_id: u_id))
        self.workgroup_mock = self.make_patch(
            self.block_to_test, 'workgroup', mock.PropertyMock(return_value=self.workgroup_data)
        )
        self.user_id_mock = self.make_patch(
            self.block_to_test, 'user_id', mock.PropertyMock(return_value=self.user_id)
        )


@ddt.ddt
class EvaluationStagesBaseTestMixin(object):
    def setUp(self):
        super(EvaluationStagesBaseTestMixin, self).setUp()

        self.available_now_mock = self.make_patch(
            self.block_to_test, 'available_now', mock.PropertyMock(return_value=True)
        )
        self.is_group_member_mock = self.make_patch(
            self.block_to_test, 'is_group_member', mock.PropertyMock(return_value=True)
        )

    @ddt.data(
        (False, False, False),
        (True, False, False),
        (False, True, False),
        (True, True, True),
    )
    @ddt.unpack
    def test_can_mark_complete_base_conditions(self, available_now, is_group_member, should_proceed_calculation):
        self.available_now_mock.return_value = available_now
        self.is_group_member_mock.return_value = is_group_member
        result = self.block.can_mark_complete

        self.assert_proceeds_calculation(should_proceed_calculation)

        if not available_now or not is_group_member:
            self.assertFalse(result)

    @ddt.data(
        (False, False),
        (True, True)
    )
    @ddt.unpack
    def test_marks_complete_on_student_view(self, can_mark_complete, should_call_mark_complete):
        can_mark_mock = mock.PropertyMock(return_value=can_mark_complete)
        with mock.patch.object(self.block_to_test, 'can_mark_complete', can_mark_mock):
            self.block.student_view({})

            if should_call_mark_complete:
                self.runtime_mock.publish.assert_called_with(self.block, 'progress', {'user_id': self.block.user_id})
            else:
                self.assertFalse(self.project_api_mock.mark_as_complete.called)


@ddt.ddt
class TestEvaluationDisplayStage(EvaluationStagesBaseTestMixin, BaseStageTest):
    block_to_test = EvaluationDisplayStage

    def setUp(self):
        super(TestEvaluationDisplayStage, self).setUp()

        self.team_members_mock = self.make_patch(self.block_to_test, 'team_members', mock.PropertyMock(return_value=[]))
        self.get_reviews_mock = self.make_patch(self.block, 'get_reviews')
        self.get_reviewer_ids_mock = self.make_patch(self.block, 'get_reviewer_ids')

    def assert_proceeds_calculation(self, should_perform_expensive_part):
        if should_perform_expensive_part:
            self.assertTrue(self.get_reviews_mock.called)
            self.assertTrue(self.get_reviewer_ids_mock.called)
        else:
            self.assertFalse(self.get_reviews_mock.called)
            self.assertFalse(self.get_reviewer_ids_mock.called)

    # pylint: disable=invalid-name
    def test_can_mark_complete_no_reviewers_returns_true(self):
        self.team_members_mock.return_value = []

        self.assertTrue(self.block.can_mark_complete)

    # pylint: disable=invalid-name
    def test_can_mark_complete_no_questions_returns_true(self):
        with mock.patch.object(self.block_to_test, 'required_questions') as patched_required_questions:
            patched_required_questions.return_value = []

            self.assertTrue(self.block.can_mark_complete)

    @ddt.data(
        ([10], ["q1"], [], False),
        ([10], ["q1"], [make_review_item(10, "q1")], True),
        ([10], ["q1"], [make_review_item(10, "q1"), make_review_item(10, "q2")], True),
        ([10], ["q1"], [make_review_item(11, "q1")], False),
        ([10], ["q1"], [make_review_item(10, "q2"), make_review_item(11, "q1")], False),
        ([10, 11], ["q1"], [make_review_item(10, "q1"), make_review_item(11, "q1")], True),
        ([10, 11], ["q1", "q2"], [make_review_item(10, "q1"), make_review_item(11, "q1")], False),
    )
    @ddt.unpack
    def test_can_mark_compete_suite(self, reviewers, questions, reviews, expected_result):
        self.get_reviewer_ids_mock.return_value = reviewers
        self.get_reviews_mock.return_value = reviews

        with mock.patch.object(
            self.block_to_test, 'required_questions', mock.PropertyMock()
        ) as patched_required_questions:
            patched_required_questions.return_value = questions

            self.assertEqual(self.block.can_mark_complete, expected_result)


@ddt.ddt
class TestGradeDisplayStage(EvaluationStagesBaseTestMixin, BaseStageTest):
    block_to_test = GradeDisplayStage

    def setUp(self):
        super(TestGradeDisplayStage, self).setUp()
        self.project_api_mock.get_workgroup_reviewers.return_value = [{"id": 1}]

    def assert_proceeds_calculation(self, should_perform_expensive_part):
        if should_perform_expensive_part:
            self.assertTrue(self.activity_mock.calculate_grade.called)
        else:
            self.assertFalse(self.activity_mock.calculate_grade.called)

    @ddt.data(
        (None, False),
        (10, True),
        (15, True)
    )
    @ddt.unpack
    def test_can_mark_compete_suite(self, calculate_grade_result, expected_result):
        self.activity_mock.calculate_grade.return_value = calculate_grade_result

        self.assertEqual(self.block.can_mark_complete, expected_result)