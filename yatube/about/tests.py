from http import HTTPStatus

from django.test import TestCase, Client


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.static_pages = {
            '/about/author/': 'about/author.html',
            '/about/tech/': 'about/tech.html',
        }

    def test_about_urls_exist_at_desired_locations(self):
        for url in self.static_pages.keys():
            with self.subTest(url=url):
                self.assertEqual(self.guest_client.get(url).status_code,
                                 HTTPStatus.OK)

    def test_about_urls_use_correct_templates(self):
        for url, template in self.static_pages.items():
            with self.subTest(url=url):
                self.assertTemplateUsed(self.guest_client.get(url), template)
