from django.test import TestCase, Client


UNEXISTING_PAGE = '/unexisting_page/'


class CustomErrorPages(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest = Client()

    def test_404_template_used(self):
        self.assertTemplateUsed(self.guest.get(UNEXISTING_PAGE),
                                'core/404.html')
